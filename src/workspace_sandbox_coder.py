"""Headless, mirror-confined coding agent — the codegen step of the sandbox pipeline.

This is the missing link between "create a dev-mirror" and "package a patch": it
drives ``stream_agent_loop`` with execution tools enabled (``sandbox_build=True``)
but confined to a per-session dev-mirror copy, in a full iterate loop (write code
-> run build/tests -> read failures -> fix -> repeat). It NEVER touches the live
repo; the orchestrator packages the resulting diff for human review/apply.

Safety: ``sandbox_build`` is honored by the agent loop only when an admin/single-user
owner AND a bound workspace are present (it fails closed otherwise), and all of the
agent's bash/python subprocesses run under the resource limits bound here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from src import tool_execution
from src.tool_execution import vet_workspace
from src.tool_security import owner_is_admin_or_single_user

# The coding toolset handed to the agent. Passing a non-empty relevant_tools set
# bypasses RAG tool selection (agent_loop: _relevant_tools is used as-is), so the
# coder always has exactly the file + shell tools it needs, regardless of prompt.
SANDBOX_CODING_TOOLS = {
    "read_file", "write_file", "edit_file", "multi_edit", "delete_file", "move_file",
    "grep", "glob", "ls",
    "get_workspace", "bash", "python", "run_tests", "git", "lint_format", "apply_patch",
}

# Per-process resource caps for the agent's bash/python during the sandbox run.
# See src/agent_tools/subprocess_tools.py::_sandbox_preexec. AS is set generously
# (a tripwire, not a throttle — too-low virtual-memory caps break legit Python).
SANDBOX_LIMITS: dict[str, int] = {
    "cpu_s": 240,
    "as_bytes": 4 * 1024 ** 3,
    "fsize": 512 * 1024 ** 2,
    "nofile": 1024,
    "timeout": 300,
}

# Sandbox-specific addendum layered on top of the shared coding brief
# (src/coding_prompt.py). The shared brief supplies the engineering workflow +
# verify discipline; this adds the isolated-sandbox framing.
_SANDBOX_ADDENDUM = """SANDBOX CONTEXT:
You are working INSIDE an isolated, disposable copy of the project at:
__WORKSPACE__
Nothing here affects the live system — when you finish, your changes become a patch
that a human reviews and approves before anything is applied. Work confidently, but:
- Stay inside this folder and use RELATIVE paths only (e.g. "src/foo.py").
- Do NOT run git commit, git push, or any git history/remote command.
- Do NOT start long-lived servers; keep commands short and bounded.
Keep iterating (edit → build/test → read failures → fix) until the build and tests
pass (at minimum: python3 -m compileall -q src; pytest -q if tests exist) or you
genuinely cannot make further progress — then stop and summarize what you changed
and the final check result.

TASK:
"""


def _build_messages(prompt: str, workspace: str) -> list[dict]:
    from src.coding_prompt import CODING_SYSTEM_PROMPT
    # Reference knowledge-pack injection is centralized in stream_agent_loop
    # (serves chat/cowork/sandbox alike) — see agent_loop.py.
    system = CODING_SYSTEM_PROMPT + "\n\n" + _SANDBOX_ADDENDUM.replace("__WORKSPACE__", workspace)
    msgs = [{"role": "system", "content": system}]
    msgs.append({"role": "user", "content": str(prompt).strip()})
    return msgs


def _write_status(status_path: Optional[str], data: dict) -> None:
    """Merge-update the per-run status JSON so an HTTP poller can watch progress."""
    if not status_path:
        return
    try:
        p = Path(status_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {}
        if p.exists():
            try:
                existing = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing.update(data)
        p.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        pass


async def run_sandbox_coding(
    *,
    mirror_path: str,
    run_id: str,
    prompt: str,
    owner: str,
    session_id: Optional[str] = None,
    endpoint_url: str,
    model: str,
    headers: Optional[dict] = None,
    max_rounds: int = 40,
    status_path: Optional[str] = None,
    temperature: float = 0.6,
    extra_brief: Optional[str] = None,
    state_label: str = "coding",
) -> dict:
    """Run the headless iterate loop confined to ``mirror_path``.

    Returns a result dict; the orchestrator re-runs the authoritative checks and
    packages the patch (it does not trust the model's self-report of "tests pass").
    """
    if not owner_is_admin_or_single_user(owner):
        return {"status": "BLOCKED_NOT_ADMIN", "run_id": run_id}
    ws = vet_workspace(mirror_path)
    if not ws:
        return {"status": "BLOCKED_INVALID_WORKSPACE", "run_id": run_id, "mirror_path": str(mirror_path)}

    from src.agent_loop import stream_agent_loop

    messages = _build_messages(prompt, ws)
    # Steer this candidate toward a particular approach (design-panel diversity).
    if extra_brief:
        messages.insert(1, {"role": "system", "content": str(extra_brief)})
    full = ""
    tool_events: list[dict] = []
    round_num = 1
    error: Optional[str] = None

    _write_status(status_path, {"state": state_label, "rounds": 0})

    # Bind resource limits for this turn's bash/python BEFORE draining the
    # generator (the generator's tool calls run in this task, so the contextvar
    # propagates), and always reset in finally.
    limit_token = tool_execution.set_sandbox_limits(SANDBOX_LIMITS)
    try:
        async for chunk in stream_agent_loop(
            endpoint_url, model, messages,
            headers=headers,
            temperature=temperature,                  # higher = more diverse/creative
            session_id=session_id,
            owner=owner,                              # admin -> execution tools unblocked
            relevant_tools=set(SANDBOX_CODING_TOOLS),  # bypass RAG selection
            max_rounds=max_rounds,                    # the iterate-loop bound
            workspace=ws,                             # confine file tools + cwd=mirror
            tool_policy=None,                         # no guide_only / no copy-only policy
            plan_mode=False,
            sandbox_build=True,                       # skip safe-local abstention strip + prose
        ):
            if not chunk.startswith("data: "):
                continue
            body = chunk[6:].strip()
            if not body or body == "[DONE]":
                continue
            try:
                d = json.loads(body)
            except (ValueError, TypeError):
                continue
            if not isinstance(d, dict):
                continue
            if "delta" in d:
                delta = d.get("delta")
                if isinstance(delta, str) and not d.get("thinking"):
                    full += delta
            elif d.get("type") == "agent_step":
                round_num = d.get("round", round_num)
                _write_status(status_path, {"rounds": round_num})
            elif d.get("type") == "tool_output":
                tool_events.append({
                    "round": round_num,
                    "tool": d.get("tool"),
                    "command": d.get("command"),
                    "exit_code": d.get("exit_code"),
                })
    except Exception as exc:  # never raise out of the headless drain
        error = str(exc)[:500]
    finally:
        tool_execution.reset_sandbox_limits(limit_token)

    status = "PASS_SANDBOX_CODING" if error is None else "ERROR_SANDBOX_CODING"
    _write_status(status_path, {
        "coding_status": status,
        "rounds": round_num,
        "tool_call_count": len(tool_events),
    })
    return {
        "status": status,
        "run_id": run_id,
        "rounds": round_num,
        "tool_call_count": len(tool_events),
        "final_text": full[-4000:],
        "error": error,
    }
