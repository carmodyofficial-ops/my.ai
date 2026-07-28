"""Cowork — terminal/CLI endpoint for my.ai.

A thin, admin-token-authenticated endpoint that drives the agent loop with the
full coding toolset against a host project directory, so the `myai` terminal
client can cowork on real files. The host directory is reachable because a host
code root is bind-mounted into the container (MYAI_HOST_CODE_ROOT ->
MYAI_CONTAINER_CODE_ROOT); this endpoint maps the host path the client sends to
the corresponding container path and confines the agent's tools to it.

Auth: a Bearer `ody_` API token whose owner is admin/single-user (the global
AuthMiddleware validates the token; we authorize on the token's real owner via
effective_user()). The agent runs as that admin owner, so its tools are enabled.
"""

from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.auth_helpers import effective_user
from src.tool_security import owner_is_admin_or_single_user
from src.tool_execution import vet_workspace
from src.coding_prompt import coding_system_message

# Full coding toolset handed to the cowork agent (passed as relevant_tools so it
# is always available, not subject to RAG selection). owner=admin keeps these
# unblocked; workspace confinement (below) keeps file/shell tools inside the
# project dir the client is in.
COWORK_TOOLS = {
    "read_file", "write_file", "edit_file", "multi_edit", "delete_file", "move_file",
    "grep", "glob", "ls", "get_workspace",
    "bash", "python", "run_tests", "git", "lint_format", "code_sandbox", "apply_patch",
    "web_search", "web_fetch", "http_request",
}

# Resource caps for cowork bash/python. Generous (cowork does real builds on the
# admin's projects) but bounded — without these, cowork shell ran with NO RLIMITs
# and a 1-HOUR default timeout, so a lured/runaway command could hang or fill disk.
# (RLIMIT_NPROC is intentionally omitted: it is per-UID and the app runs as that
# UID, so it would throttle the app itself; fork-bomb containment needs a cgroup.)
COWORK_LIMITS: dict[str, int] = {
    "cpu_s": 600,
    "as_bytes": 8 * 1024 ** 3,
    "fsize": 2 * 1024 ** 3,
    "nofile": 4096,
    "timeout": 600,
}


# ── Per-command approval registry ──────────────────────────────────────────
# When a cowork stream runs with require_approval=true, the agent loop pauses
# before each mutating/effectful tool and awaits a decision from the client. The
# loop emits an `approval_required` SSE; the client POSTs /api/cowork/approve to
# resolve it. Pending decisions live here as futures keyed by approval id.
# The registry itself now lives in src/tool_approvals.py so the cowork route and
# the browser chat route share ONE implementation (they previously could not —
# chat had none at all). Semantics are unchanged: synchronous registration to
# close the resolve-before-register race, owner-scoped resolution, and a
# fail-closed TTL that denies when no decision arrives.
from src.tool_approvals import (  # noqa: E402
    make_approval_cb as _make_approval_cb,
    resolve as _resolve_approval,
)


def map_host_workspace_to_container(host_path: str) -> str | None:
    """Translate a host project path to its in-container path via the bind mount.

    Returns the container path when host_path is under MYAI_HOST_CODE_ROOT, else
    None (the agent then runs without a bound workspace — support/chat mode).
    """
    host_root = (os.environ.get("MYAI_HOST_CODE_ROOT") or "").rstrip("/")
    cont_root = (os.environ.get("MYAI_CONTAINER_CODE_ROOT") or "").rstrip("/")
    if not (host_root and cont_root and host_path):
        return None
    hp = os.path.normpath(host_path)
    if hp == host_root:
        return cont_root
    if hp.startswith(host_root + "/"):
        return cont_root + hp[len(host_root):]
    return None


def setup_cowork_routes() -> APIRouter:
    router = APIRouter(tags=["cowork"])

    def _require_cowork_admin(request: Request) -> str:
        owner = effective_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="cowork requires an admin API token")
        return owner

    @router.get("/api/cowork/health")
    async def cowork_health(request: Request):
        owner = _require_cowork_admin(request)
        return {
            "ok": True,
            "owner": owner,
            "host_code_root": os.environ.get("MYAI_HOST_CODE_ROOT"),
            "container_code_root": os.environ.get("MYAI_CONTAINER_CODE_ROOT"),
            "code_root_mounted": bool(
                os.environ.get("MYAI_CONTAINER_CODE_ROOT")
                and os.path.isdir(os.environ.get("MYAI_CONTAINER_CODE_ROOT", ""))
            ),
            "tools": sorted(COWORK_TOOLS),
        }

    @router.post("/api/cowork/stream")
    async def cowork_stream(request: Request):
        owner = _require_cowork_admin(request)
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="JSON body required")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="messages (non-empty list) required")
        # Only pass through clean role/content turns.
        clean: list[dict] = []
        for m in messages:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant", "system") and isinstance(m.get("content"), str):
                clean.append({"role": m["role"], "content": m["content"]})
        if not clean:
            raise HTTPException(status_code=400, detail="no valid messages")
        # Lead with the shared coding brief (merged into the system prompt) so the
        # cowork agent gets the senior-engineer workflow + verify discipline.
        if not (clean and clean[0].get("role") == "system"):
            clean = [coding_system_message()] + clean
        # Reference knowledge-pack injection is now centralized in
        # stream_agent_loop (serves chat/cowork/sandbox alike) — see agent_loop.py.

        host_ws = str(body.get("workspace") or "")
        cont_ws = map_host_workspace_to_container(host_ws)
        ws = vet_workspace(cont_ws) if cont_ws else None

        from src.endpoint_resolver import resolve_endpoint
        endpoint_url, model, headers = resolve_endpoint("default", owner=owner)
        req_model = (body.get("model") or os.environ.get("MYAI_COWORK_MODEL") or "").strip()
        if req_model:
            model = req_model
        if not (endpoint_url and model):
            raise HTTPException(status_code=503, detail="no model endpoint configured (set a default model or pass 'model')")

        try:
            max_rounds = int(body.get("max_rounds") or 30)
        except Exception:
            max_rounds = 30
        max_rounds = max(1, min(max_rounds, 100))

        # Opt-in per-command approval: when true, the agent pauses before each
        # mutating tool and waits for the client to approve via /api/cowork/approve.
        # Default false keeps the existing trusted, non-interactive behavior.
        require_approval = bool(body.get("require_approval", False))
        approval_cb = _make_approval_cb(owner) if require_approval else None

        async def gen():
            from src.agent_loop import stream_agent_loop
            # First event: tell the client how the workspace mapped + which model.
            yield "data: " + json.dumps({
                "type": "cowork_meta",
                "workspace_host": host_ws or None,
                "workspace_container": ws,
                "workspace_bound": bool(ws),
                "model": model,
                "owner": owner,
            }) + "\n\n"
            from src import tool_execution
            _limit_token = tool_execution.set_sandbox_limits(COWORK_LIMITS)
            try:
                async for chunk in stream_agent_loop(
                    endpoint_url, model, clean,
                    headers=headers or {}, owner=owner,
                    relevant_tools=set(COWORK_TOOLS),
                    workspace=ws,
                    max_rounds=max_rounds,
                    trusted_execution=True,
                    approval_cb=approval_cb,
                ):
                    yield chunk
            except Exception as exc:  # surface as an SSE error, never 500 mid-stream
                yield "event: error\ndata: " + json.dumps({"error": str(exc)[:300]}) + "\n\n"
            finally:
                tool_execution.reset_sandbox_limits(_limit_token)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.post("/api/cowork/approve")
    async def cowork_approve(request: Request):
        owner = _require_cowork_admin(request)
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="JSON body required")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        approval_id = str(body.get("id") or "").strip()
        approved = bool(body.get("approved", False))
        if not approval_id:
            raise HTTPException(status_code=400, detail="id is required")
        if not _resolve_approval(approval_id, approved, owner):
            raise HTTPException(status_code=404,
                                detail="no such pending approval (expired, already resolved, or not yours)")
        return {"ok": True, "id": approval_id, "approved": approved}

    return router
