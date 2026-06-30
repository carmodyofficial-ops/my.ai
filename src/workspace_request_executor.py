"""Executor that turns queued workspace requests into D42 dev/mirror runs."""

from __future__ import annotations

from pathlib import Path
import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from .workspace_code_request_queue import (
    DEFAULT_QUEUE_DIR,
    create_code_request,
    list_code_requests,
    read_code_request,
    update_code_request_status,
)

# Repo root, resolved from this file's location so it is correct both on the host
# (/home/youruser/odysseus) and inside the app container (/app) — the in-app
# sandbox endpoints run in the container, where the old hardcoded host path is absent.
ROOT = Path(__file__).resolve().parents[1]
D42_TOOLS = ROOT / "data/d42_tools"


# ---------------------------------------------------------------------------
# Dev-mirror cleanup. A mirror (data/dev_mirror/mirrors/<run_id>) is a full
# ~GB copy of the repo used only as scratch to generate + test a change. The
# DELIVERABLE is the extracted patch (data/dev_mirror/patches/<run_id>.patch,
# a few KB), which review/apply use — NOT the mirror. So once a run is packaged
# its mirror is dead weight and is removed. A stale sweep reclaims mirrors left
# by crashed/old runs, keeping a few recent ones as a safety margin.
# ---------------------------------------------------------------------------

# Idempotency: guard an accidental double-submit (a double-clicked "Build") from
# launching two full ~GB/GPU pipelines for the identical request. In-memory + short
# window — this is for rapid duplicates, not cross-restart dedup.
_IDEMPOTENCY: dict[str, tuple[str, float]] = {}


def idempotent_existing(key: str, window_s: float = 30.0) -> str | None:
    """Return the tracking_id of a very-recent identical build, or None."""
    now = time.time()
    for k in [k for k, (_, ts) in list(_IDEMPOTENCY.items()) if now - ts > window_s]:
        _IDEMPOTENCY.pop(k, None)
    hit = _IDEMPOTENCY.get(key)
    return hit[0] if (hit and now - hit[1] <= window_s) else None


def record_idempotent(key: str, tracking_id: str) -> None:
    _IDEMPOTENCY[key] = (tracking_id, time.time())


_SANDBOX_SEMAPHORE = None


def sandbox_semaphore():
    """Global gate so concurrent sandbox builds/panels don't oversubscribe the
    single local GPU (and pile up ~GB mirrors). Bound = MYAI_SANDBOX_CONCURRENCY
    (default 1). Acquire it around a whole run; queued runs wait their turn."""
    global _SANDBOX_SEMAPHORE
    if _SANDBOX_SEMAPHORE is None:
        import os as _os
        _SANDBOX_SEMAPHORE = asyncio.Semaphore(max(1, int(_os.environ.get("MYAI_SANDBOX_CONCURRENCY", "1"))))
    return _SANDBOX_SEMAPHORE


def _mirrors_base(root: Path | str = ROOT) -> Path:
    return Path(root) / "data/dev_mirror/mirrors"


def _deregister_worktree(mirror_run_dir: Path, root: Path | str = ROOT) -> None:
    """If a mirror was created as a git worktree (its repo/ has a `.git` FILE),
    deregister it with `git worktree remove` before the dir is rmtree'd, so the
    main repo's .git/worktrees registry doesn't accumulate dangling entries.
    Best-effort; never raises."""
    try:
        repo = mirror_run_dir / "repo"
        gitmark = repo / ".git"
        if gitmark.is_file():  # a worktree marks its root with a .git FILE
            subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", str(repo)],
                           text=True, capture_output=True, timeout=60)
            subprocess.run(["git", "-C", str(root), "worktree", "prune"],
                           text=True, capture_output=True, timeout=60)
    except Exception:
        pass


def remove_mirror(run_id: str, root: Path | str = ROOT) -> bool:
    """Best-effort delete of one run's mirror dir. Never raises."""
    try:
        d = _mirrors_base(root) / str(run_id)
        if d.exists():
            _deregister_worktree(d, root)
            shutil.rmtree(d, ignore_errors=True)
            return True
    except Exception:
        pass
    return False


def cleanup_stale_mirrors(root: Path | str = ROOT, keep_recent: int = 3,
                          max_age_hours: float = 2.0) -> dict[str, Any]:
    """Remove mirror dirs older than `max_age_hours`, always keeping the
    `keep_recent` newest (margin for an in-flight build/review). Best-effort;
    the patch is the durable artifact, so deleting scratch mirrors is safe."""
    try:
        base = _mirrors_base(root)
        if not base.exists():
            return {"removed": 0}
        dirs = [d for d in base.iterdir() if d.is_dir()]
        try:
            dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        except Exception:
            pass
        cutoff = time.time() - max_age_hours * 3600
        removed = 0
        for i, d in enumerate(dirs):
            if i < keep_recent:
                continue
            try:
                if d.stat().st_mtime < cutoff:
                    _deregister_worktree(d, root)
                    shutil.rmtree(d, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
        return {"removed": removed, "total_before": len(dirs)}
    except Exception as exc:
        return {"error": str(exc)[:200]}

EXECUTOR_SAFETY = {
    "patch_apply_allowed": False,
    "live_repo_modification_allowed": False,
    "commit_allowed": False,
    "push_allowed": False,
    "service_restart_allowed": False,
    "remote_command_execution_allowed": False,
    "lan_exposure_allowed": False,
    "model_endpoint_exposure_allowed": False,
    "whatsapp_outbound_allowed": False,
}


def _run_json(cmd: list[str], cwd: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=900)
    diag = {
        "cmd": cmd,
        "returncode": p.returncode,
        "stdout": p.stdout[-8000:],
        "stderr": p.stderr[-8000:],
    }
    try:
        return json.loads(p.stdout), diag
    except Exception:
        return None, diag


def next_queued_request(queue_dir: Path | str = DEFAULT_QUEUE_DIR) -> dict[str, Any] | None:
    items = list_code_requests(queue_dir=queue_dir, status="queued", limit=1)
    return items[0] if items else None


def execute_request_to_dev_mirror(
    request_id: str | None = None,
    *,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
    root: Path | str = ROOT,
    d42_tools: Path | str = D42_TOOLS,
    run_checks: bool = True,
    package_change: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    queue_dir = Path(queue_dir)
    d42_tools = Path(d42_tools)

    request = read_code_request(request_id, queue_dir=queue_dir) if request_id else next_queued_request(queue_dir)
    if not request:
        return {"status": "NO_QUEUED_REQUEST", "safety": dict(EXECUTOR_SAFETY)}

    workspace_request_id = request["request_id"]
    update_code_request_status(workspace_request_id, "executing", queue_dir=queue_dir)

    diagnostics: dict[str, Any] = {}

    d42_req, diag = _run_json([
        "python3", str(d42_tools / "create_d42_dev_request.py"),
        "--title", request.get("title", "workspace_request"),
        "--prompt", request.get("prompt", ""),
    ], root)
    diagnostics["create_d42_request"] = diag

    if not d42_req or d42_req.get("status") != "PASS_D42_DEV_REQUEST_CREATED":
        update_code_request_status(workspace_request_id, "executor_failed", queue_dir=queue_dir)
        return {"status": "FAIL_CREATE_D42_REQUEST", "workspace_request_id": workspace_request_id, "diagnostics": diagnostics, "safety": dict(EXECUTOR_SAFETY)}

    d42_mirror, diag = _run_json([
        "python3", str(d42_tools / "create_d42_dev_mirror.py"),
        "--request-id", d42_req["request_id"],
    ], root)
    diagnostics["create_d42_mirror"] = diag

    if not d42_mirror or d42_mirror.get("status") != "PASS_D42_DEV_MIRROR_CREATED":
        update_code_request_status(workspace_request_id, "executor_failed", queue_dir=queue_dir)
        return {"status": "FAIL_CREATE_D42_MIRROR", "workspace_request_id": workspace_request_id, "d42_request_id": d42_req["request_id"], "diagnostics": diagnostics, "safety": dict(EXECUTOR_SAFETY)}

    checks_status = "SKIPPED"
    if run_checks:
        checks, diag = _run_json([
            "python3", str(d42_tools / "run_d42_dev_mirror_checks.py"),
            "--run-id", d42_mirror["run_id"],
        ], root)
        diagnostics["checks"] = diag
        checks_status = (checks or {}).get("status", "UNKNOWN")

    package_status = "SKIPPED"
    patch_file = None
    if package_change:
        package, diag = _run_json([
            "python3", str(d42_tools / "package_d42_dev_change.py"),
            "--run-id", d42_mirror["run_id"],
        ], root)
        diagnostics["package"] = diag
        package_status = (package or {}).get("status", "UNKNOWN")
        patch_file = (package or {}).get("patch_file")

    update_code_request_status(workspace_request_id, "dev_mirror_packaged", queue_dir=queue_dir)

    return {
        "status": "PASS_WORKSPACE_REQUEST_EXECUTED_TO_DEV_MIRROR",
        "workspace_request_id": workspace_request_id,
        "d42_request_id": d42_req["request_id"],
        "d42_run_id": d42_mirror["run_id"],
        "mirror_path": d42_mirror["mirror_path"],
        "checks_status": checks_status,
        "package_status": package_status,
        "patch_file": patch_file,
        "diagnostics": diagnostics,
        "safety": dict(EXECUTOR_SAFETY),
    }


# ---------------------------------------------------------------------------
# Per-session sandbox coding pipeline (async): create_request -> mirror ->
# CODEGEN (the missing link) -> authoritative checks -> package -> ready for
# review. Status is tracked by a caller-supplied tracking_id so an HTTP poller
# can watch progress; the d42 run_id is recorded inside. Like the executor
# above, this never touches the live repo.
# ---------------------------------------------------------------------------

SANDBOX_RUNS_DIR = ROOT / "data/dev_mirror/sandbox_runs"


def _sandbox_status_path(tracking_id: str) -> Path:
    return SANDBOX_RUNS_DIR / f"{tracking_id}.json"


def _write_sandbox_status(tracking_id: str, data: dict[str, Any]) -> None:
    """Merge-update the per-run status JSON (poller-readable)."""
    try:
        SANDBOX_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = _sandbox_status_path(tracking_id)
        existing: dict[str, Any] = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing.update(data)
        existing["tracking_id"] = tracking_id
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        pass


def read_sandbox_status(tracking_id: str) -> dict[str, Any] | None:
    path = _sandbox_status_path(tracking_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_sandbox_statuses(limit: int = 25) -> list[dict[str, Any]]:
    if not SANDBOX_RUNS_DIR.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in SANDBOX_RUNS_DIR.glob("*.json"):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    items.sort(key=lambda it: (it.get("created_at") or "", it.get("tracking_id") or ""), reverse=True)
    return items[: max(0, int(limit))]


def _sandbox_fail(tracking_id: str, error_status: str, diagnostics: Any) -> dict[str, Any]:
    logger.warning("[sandbox] run %s failed: %s — %s", tracking_id, error_status, str(diagnostics)[:300])
    _write_sandbox_status(tracking_id, {
        "state": "error",
        "error_status": error_status,
        "diagnostics": diagnostics,
    })
    return read_sandbox_status(tracking_id) or {"state": "error", "error_status": error_status}


def seed_sandbox_status(tracking_id: str, *, prompt: str, owner: str, session_id: str | None) -> None:
    """Pre-seed a queued status synchronously so the launch endpoint can return a
    poll handle before the (slow) background pipeline starts."""
    _write_sandbox_status(tracking_id, {
        "state": "queued",
        "prompt": str(prompt)[:2000],
        "owner": owner,
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Operability: orphaned-run recovery, retention pruning, and a health summary.
# A sandbox run is a fire-and-forget asyncio task with file-only status — so an
# app restart orphans any in-flight run (its task dies, the poller hangs forever)
# and nothing ever reclaims old status/patch/envelope files.
# ---------------------------------------------------------------------------

_TERMINAL_STATES = {"done", "error", "cancelled"}


def _runs_dir(root: Path | str = ROOT) -> Path:
    return Path(root) / "data/dev_mirror/sandbox_runs"


def recover_orphaned_runs(root: Path | str = ROOT) -> dict[str, Any]:
    """Mark non-terminal runs as aborted. On startup every in-flight run is dead
    (its task died with the previous process), so flip it to error rather than
    leaving the poller stuck on 'coding' forever."""
    base = _runs_dir(root)
    recovered = 0
    try:
        if not base.exists():
            return {"recovered": 0}
        for path in base.glob("*.json"):
            try:
                st = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(st.get("state")) in _TERMINAL_STATES:
                continue
            st.update({"state": "error", "error_status": "ABORTED_APP_RESTART",
                       "updated_at": datetime.now(timezone.utc).isoformat()})
            try:
                path.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                recovered += 1
            except Exception:
                continue
    except Exception as exc:
        return {"error": str(exc)[:200]}
    if recovered:
        logger.warning("[sandbox] recovered %d orphaned run(s) at startup", recovered)
    return {"recovered": recovered}


def prune_sandbox_artifacts(root: Path | str = ROOT, keep_runs: int = 60,
                            max_age_hours: float = 72.0) -> dict[str, Any]:
    """Bound the monotonic growth of run status files, run envelopes, and throwaway
    .pre_repair.patch snapshots. Keeps the `keep_runs` newest status files; among
    older ones removes those past max_age_hours. NEVER deletes a primary patch (the
    deliverable, KB-scale) — only the pre-repair snapshots."""
    root = Path(root)
    removed = {"statuses": 0, "envelopes": 0, "pre_repair_patches": 0}
    cutoff = time.time() - max_age_hours * 3600
    try:
        runs = _runs_dir(root)
        if runs.exists():
            files = sorted(runs.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for i, p in enumerate(files):
                if i < keep_runs:
                    continue
                try:
                    if p.stat().st_mtime < cutoff:
                        p.unlink()
                        removed["statuses"] += 1
                except Exception:
                    continue
        env_dir = root / "data/dev_mirror/runs"
        if env_dir.exists():
            for d in env_dir.iterdir():
                try:
                    if d.is_dir() and d.stat().st_mtime < cutoff:
                        shutil.rmtree(d, ignore_errors=True)
                        removed["envelopes"] += 1
                except Exception:
                    continue
        patch_dir = root / "data/dev_mirror/patches"
        if patch_dir.exists():
            for p in patch_dir.glob("*.pre_repair.patch"):
                try:
                    if p.stat().st_mtime < cutoff:
                        p.unlink()
                        removed["pre_repair_patches"] += 1
                except Exception:
                    continue
    except Exception as exc:
        return {"error": str(exc)[:200], **removed}
    return removed


def sandbox_health(root: Path | str = ROOT) -> dict[str, Any]:
    """Observable summary of background sandbox runs (counts by state, in-flight,
    oldest in-flight, mirror disk) — so pipeline health doesn't require per-id polling."""
    from collections import Counter
    counts: Counter = Counter()
    oldest_inflight = None
    total = 0
    runs = _runs_dir(root)
    if runs.exists():
        for p in runs.glob("*.json"):
            try:
                st = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            total += 1
            state = str(st.get("state") or "unknown")
            counts[state] += 1
            if state not in _TERMINAL_STATES:
                ca = st.get("created_at") or st.get("updated_at")
                if ca and (oldest_inflight is None or ca < oldest_inflight):
                    oldest_inflight = ca
    mb = _mirrors_base(root)
    mirror_dirs = len([d for d in mb.iterdir() if d.is_dir()]) if mb.exists() else 0
    in_flight = sum(v for k, v in counts.items() if k not in _TERMINAL_STATES)
    return {
        "total_runs": total,
        "in_flight": in_flight,
        "errors": counts.get("error", 0),
        "by_state": dict(counts),
        "oldest_in_flight_created_at": oldest_inflight,
        "mirror_dirs": mirror_dirs,
        "concurrency_limit": int(os.environ.get("MYAI_SANDBOX_CONCURRENCY", "1") or 1),
    }


def housekeeping_on_startup(root: Path | str = ROOT) -> dict[str, Any]:
    """Run on app boot: recover orphaned runs, reclaim stale mirrors, prune old
    artifacts. Best-effort; never raises into startup."""
    try:
        rec = recover_orphaned_runs(root)
        cln = cleanup_stale_mirrors(root, keep_recent=0, max_age_hours=0.0)
        prn = prune_sandbox_artifacts(root)
        logger.info("[sandbox] startup housekeeping: recovered=%s mirrors_removed=%s pruned=%s",
                    rec.get("recovered"), cln.get("removed"), prn)
        return {"recovered": rec, "mirrors": cln, "pruned": prn}
    except Exception as exc:
        logger.warning("[sandbox] startup housekeeping failed: %s", exc)
        return {"error": str(exc)[:200]}


async def launch_sandbox_build(
    prompt: str,
    *,
    owner: str,
    session_id: str | None = None,
    candidates: int = 1,
    max_rounds: int = 40,
    temperature: float = 0.6,
    model: str | None = None,
) -> dict[str, Any]:
    """Resolve a model endpoint and enqueue a sandbox build (or, when
    ``candidates`` > 1, a design panel) as a background task.

    Single source of truth shared by the HTTP route (/api/workspace/sandbox/
    build) and the in-chat ``request_sandbox_build`` agent tool. Returns a status
    dict; on failure returns ``{"ok": False, "error": ...}`` rather than raising
    so either caller can surface it. Nothing touches the live repo — the only
    deliverable is a human-reviewable patch.
    """
    import secrets as _secrets
    import hashlib as _hashlib

    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt is required"}
    candidates = max(1, min(int(candidates or 1), 4))
    try:
        max_rounds = max(1, min(int(max_rounds or 40), 100))
    except Exception:
        max_rounds = 40
    try:
        temperature = max(0.0, min(float(temperature), 1.2))
    except Exception:
        temperature = 0.6

    # Resolve the model endpoint: prefer the originating session's config, else
    # the configured default — same precedence as the HTTP route.
    endpoint_url = None
    headers: dict = {}
    resolved_model = None
    if session_id:
        try:
            from src.ai_interaction import get_session_manager
            sess = get_session_manager().get_session(session_id)
            if sess and getattr(sess, "endpoint_url", None) and getattr(sess, "model", None):
                endpoint_url = sess.endpoint_url
                resolved_model = sess.model
                headers = getattr(sess, "headers", None) or {}
        except Exception:
            pass
    if not (endpoint_url and resolved_model):
        try:
            from src.endpoint_resolver import resolve_endpoint
            endpoint_url, resolved_model, headers = resolve_endpoint("default", owner=owner)
            headers = headers or {}
        except Exception:
            endpoint_url = resolved_model = None
    if model and endpoint_url:
        resolved_model = str(model)
    if not (endpoint_url and resolved_model):
        return {"ok": False,
                "error": "no model endpoint configured for sandbox builds; open a chat with a model selected first"}

    # Idempotency: a repeated identical submit returns the in-flight run instead
    # of launching a second full pipeline.
    _idem = _hashlib.sha256(f"{owner}|{session_id}|{candidates}|{prompt}".encode()).hexdigest()[:16]
    _existing = idempotent_existing(_idem)
    if _existing:
        return {"ok": True, "tracking_id": _existing, "deduped": True,
                "poll": f"/api/workspace/sandbox/runs/{_existing}",
                "message": "An identical build was just submitted; returning that run."}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tracking_id = f"sbx_{stamp}_{_secrets.token_hex(4)}"
    record_idempotent(_idem, tracking_id)
    seed_sandbox_status(tracking_id, prompt=prompt, owner=owner, session_id=session_id)

    async def _runner():
        # One sandbox run at a time (GPU/mirror bound); waiting runs sit queued.
        async with sandbox_semaphore():
            try:
                if candidates > 1:
                    await execute_sandbox_design_panel(
                        tracking_id=tracking_id, prompt=prompt, owner=owner,
                        session_id=session_id, endpoint_url=endpoint_url, model=resolved_model,
                        headers=headers, candidates=candidates, max_rounds=max_rounds,
                    )
                else:
                    await execute_sandbox_coding_request(
                        tracking_id=tracking_id, prompt=prompt, owner=owner,
                        session_id=session_id, endpoint_url=endpoint_url, model=resolved_model,
                        headers=headers, max_rounds=max_rounds, temperature=temperature,
                    )
            except Exception:
                # The executor records error state; this is a last-resort guard so
                # a stray exception can't crash the background task.
                pass

    asyncio.create_task(_runner())
    _msg = (("Design panel started: generating %d distinct candidate solutions, testing each, "
             "and a judge will pick the best. Nothing touches the live repo." % candidates)
            if candidates > 1 else
            "Sandbox build started. Code is generated and tested in an isolated dev-mirror; "
            "nothing touches the live repo until you review and approve the patch.")
    return {"ok": True, "tracking_id": tracking_id, "state": "queued",
            "mode": "design_panel" if candidates > 1 else "sandbox_build",
            "candidates": candidates,
            "poll": f"/api/workspace/sandbox/runs/{tracking_id}",
            "automatic_execution": False, "message": _msg}


async def execute_sandbox_coding_request(
    *,
    tracking_id: str,
    prompt: str,
    owner: str,
    session_id: str | None,
    endpoint_url: str,
    model: str,
    headers: dict | None = None,
    title: str = "sandbox_build",
    max_rounds: int = 40,
    temperature: float = 0.6,
    review_repair: bool = True,
    generate_tests: bool = True,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
    root: Path | str = ROOT,
    d42_tools: Path | str = D42_TOOLS,
) -> dict[str, Any]:
    root = Path(root)
    d42_tools = Path(d42_tools)
    queue_dir = Path(queue_dir)

    _write_sandbox_status(tracking_id, {
        "state": "mirroring",
        "prompt": str(prompt)[:2000],
        "owner": owner,
        "session_id": session_id,
        "created_at": (read_sandbox_status(tracking_id) or {}).get("created_at")
        or datetime.now(timezone.utc).isoformat(),
    })

    run_id = None
    try:
        cleanup_stale_mirrors(root)  # backstop: reclaim mirrors left by crashed runs
        # 1. Queue intake (records the request + links it to this session/tracking id).
        req = create_code_request(
            prompt, title, queue_dir=queue_dir,
            metadata={"mode": "sandbox_build", "owner": owner,
                      "session_id": session_id, "tracking_id": tracking_id},
        )
        workspace_request_id = req["request_id"]

        # 2. D42 dev request + mirror (blocking subprocess -> thread).
        d42_req, diag1 = await asyncio.to_thread(
            _run_json,
            ["python3", str(d42_tools / "create_d42_dev_request.py"),
             "--title", title, "--prompt", prompt],
            root,
        )
        if not d42_req or d42_req.get("status") != "PASS_D42_DEV_REQUEST_CREATED":
            update_code_request_status(workspace_request_id, "executor_failed", queue_dir=queue_dir)
            return _sandbox_fail(tracking_id, "FAIL_CREATE_D42_REQUEST", diag1)

        d42_mirror, diag2 = await asyncio.to_thread(
            _run_json,
            ["python3", str(d42_tools / "create_d42_dev_mirror.py"),
             "--request-id", d42_req["request_id"]],
            root,
        )
        if not d42_mirror or d42_mirror.get("status") != "PASS_D42_DEV_MIRROR_CREATED":
            update_code_request_status(workspace_request_id, "executor_failed", queue_dir=queue_dir)
            return _sandbox_fail(tracking_id, "FAIL_CREATE_D42_MIRROR", diag2)

        run_id = d42_mirror["run_id"]
        mirror_path = d42_mirror["mirror_path"]
        _write_sandbox_status(tracking_id, {
            "state": "coding",
            "d42_run_id": run_id,
            "mirror_path": mirror_path,
            "workspace_request_id": workspace_request_id,
        })
        update_code_request_status(workspace_request_id, "sandbox_coding", queue_dir=queue_dir)

        # 3. CODEGEN — the missing link: run the agent into the mirror (iterate loop).
        from src.workspace_sandbox_coder import run_sandbox_coding
        coding = await run_sandbox_coding(
            mirror_path=mirror_path, run_id=run_id, prompt=prompt,
            owner=owner, session_id=session_id,
            endpoint_url=endpoint_url, model=model, headers=headers,
            max_rounds=max_rounds, status_path=str(_sandbox_status_path(tracking_id)),
            temperature=temperature,
        )

        # 3b. TEST-GENERATION GATE: package an interim diff, write a focused test for
        # it into the mirror so the authoritative checks below actually RUN it (via
        # pytest_changed) and it ships in the patch the human reviews — functional
        # verification, not just compilation. Best-effort; a checks failure here is a
        # real signal that drives review-repair.
        test_info: dict[str, Any] = {"test_generated": False}
        if generate_tests:
            _write_sandbox_status(tracking_id, {"state": "writing_test"})
            _pkg0, _ = await asyncio.to_thread(
                _run_json, ["python3", str(d42_tools / "package_d42_dev_change.py"), "--run-id", run_id], root)
            _diff0 = _read_patch_text(root, (_pkg0 or {}).get("patch_file"), max_chars=4000)
            if _diff0:
                _tg = await _generate_test(prompt, _diff0, mirror_path, endpoint_url, model, headers)
                test_info = {"test_generated": bool(_tg.get("generated")), "test_file": _tg.get("test_file")}

        # 4. Authoritative checks (do NOT trust the model's self-report).
        _write_sandbox_status(tracking_id, {"state": "checking"})
        checks, diag3 = await asyncio.to_thread(
            _run_json,
            ["python3", str(d42_tools / "run_d42_dev_mirror_checks.py"), "--run-id", run_id],
            root,
        )
        checks_status = (checks or {}).get("status", "UNKNOWN")
        hard_failures = (checks or {}).get("hard_failure_count")

        # 5. Package the clean patch (read-only difflib live<->mirror).
        _write_sandbox_status(tracking_id, {"state": "packaging"})
        package, diag4 = await asyncio.to_thread(
            _run_json,
            ["python3", str(d42_tools / "package_d42_dev_change.py"), "--run-id", run_id],
            root,
        )
        package_status = (package or {}).get("status", "UNKNOWN")
        patch_file = (package or {}).get("patch_file")
        changed = (package or {}).get("changed_file_count")

        # 5b. REVIEW & REPAIR (monotonic) — critique the diff, fix real issues, and
        # keep the better of original vs repaired. Factored into _review_and_repair
        # so the design panel reuses the exact same logic per candidate.
        review_info: dict[str, Any] = {"review_repair": review_repair, "review_repair_applied": False}
        if review_repair:
            _write_sandbox_status(tracking_id, {"state": "reviewing"})
            rr = await _review_and_repair(
                prompt=prompt, mirror_path=mirror_path, run_id=run_id, owner=owner,
                session_id=session_id, endpoint_url=endpoint_url, model=model, headers=headers,
                d42_tools=d42_tools, root=root, patch_file=patch_file,
                checks_status=checks_status, changed=changed, max_rounds=max_rounds,
                status_path=str(_sandbox_status_path(tracking_id)),
            )
            patch_file, checks_status, changed = rr["patch_file"], rr["checks_status"], rr["changed"]
            if rr.get("package_status"):
                package_status = rr["package_status"]
            review_info.update(rr["info"])

        update_code_request_status(workspace_request_id, "sandbox_packaged", queue_dir=queue_dir)
        review_url = f"/workspace/patch-review?patch={patch_file}" if patch_file else None

        _write_sandbox_status(tracking_id, {
            "state": "done",
            "coding_status": coding.get("status"),
            "coding_error": coding.get("error"),
            "rounds": coding.get("rounds"),
            "tool_call_count": coding.get("tool_call_count"),
            "checks_status": checks_status,
            "hard_failure_count": hard_failures,
            "package_status": package_status,
            "patch_file": patch_file,
            "changed_file_count": changed,
            "review_url": review_url,
            **test_info,
            **review_info,
        })
        logger.info("[sandbox] build %s done: checks=%s changed=%s repair=%s",
                    tracking_id, checks_status, changed, review_info.get("repair_kept"))
        return read_sandbox_status(tracking_id) or {}
    except Exception as exc:  # never leave a run hung
        return _sandbox_fail(tracking_id, "ERROR_SANDBOX_PIPELINE", {"error": str(exc)[:500]})
    finally:
        # Patch is the deliverable; the ~GB mirror is scratch — drop it on EVERY
        # exit (success or error) so a failed run can't leak its mirror.
        if run_id:
            remove_mirror(run_id, root)


# ---------------------------------------------------------------------------
# Design panel (best-of-N): generate several genuinely-different candidate
# solutions in parallel sandboxes, check each, and have a judge pick the best.
# This samples the model's distribution multiple times and keeps the tail —
# where original, well-fitted code lives — instead of the single most-probable
# (= most generic) one-shot. Async, opt-in. Never touches the live repo.
# ---------------------------------------------------------------------------

_APPROACH_FRAMINGS = [
    "DESIGN DIRECTION A — Prioritize the SIMPLEST design that makes the problem easy: the clearest data model and the fewest moving parts. Resist structure you don't need.",
    "DESIGN DIRECTION B — Prioritize a CLEAN, EXTENSIBLE structure that's easy to extend with new cases/features later, without over-engineering.",
    "DESIGN DIRECTION C — Take a genuinely DIFFERENT angle than the obvious one: a different data structure or paradigm (table/config-driven, declarative, or borrow a pattern like a state machine / pipeline / registry). Avoid the textbook template.",
    "DESIGN DIRECTION D — Optimize for ROBUSTNESS and edge-case correctness: find the inputs that break a naive solution and handle them cleanly.",
]


def _read_patch_text(root: Path, patch_file: str | None, max_chars: int = 1600) -> str:
    if not patch_file:
        return ""
    try:
        return (Path(root) / patch_file).read_text(errors="replace")[:max_chars]
    except Exception:
        return ""


async def _judge_candidates(task: str, candidates: list[dict], endpoint_url: str,
                            model: str, headers: dict | None) -> tuple[int | None, str]:
    """Pick the best candidate. Returns (winner_idx_or_None, reason)."""
    lines = [f"TASK:\n{task}\n", "CANDIDATE SOLUTIONS (same task, different designs):"]
    for c in candidates:
        lines.append(f"\n--- Candidate {c['idx']} ({c['label']}) ---")
        lines.append(f"checks: {c.get('checks_status')} (hard_failures={c.get('hard_failures')}), files changed: {c.get('changed')}")
        lines.append("diff:\n" + (c.get("diff") or "(empty)"))
    lines.append(
        "\n\nYou are a senior engineer judging these candidate solutions to the SAME task. "
        "Pick the single BEST one. Weigh, in order: (1) correctness — passes checks and handles the real cases; "
        "(2) fit & quality — the design that best fits THIS problem, the simplest that makes it easy, readable and tailored (generic/boilerplate is worse); "
        "(3) originality only where it genuinely produces a better-fitted design, never cleverness for its own sake. "
        "A candidate that fails checks loses to one that passes, unless all fail.\n"
        "Reply with ONLY the candidate number on the FIRST line (e.g. `2`), then one sentence explaining why it wins."
    )
    try:
        from src.llm_core import llm_call_async
        out = await llm_call_async(
            endpoint_url, model, [{"role": "user", "content": "\n".join(lines)}],
            temperature=0.2, max_tokens=300, headers=headers or {},
        )
        import re as _re
        m = _re.search(r"[1-9][0-9]?", out or "")
        return (int(m.group(0)) if m else None), (out or "").strip()[:400]
    except Exception as exc:
        return None, f"judge_failed: {exc}"


async def _review_diff(task: str, diff: str, endpoint_url: str, model: str,
                       headers: dict | None) -> tuple[str, bool]:
    """Critique a diff for real defects. Returns (issues_text, has_real_issues)."""
    prompt = (
        f"TASK:\n{task}\n\nDIFF (the change to review):\n{diff}\n\n"
        "You are a STRICT senior code reviewer. Find only REAL, concrete problems in this diff: "
        "correctness bugs, unhandled edge cases (empty / None / zero / negative / very large inputs), "
        "requirements from the task that are missed, security issues, or resource leaks. For each, give "
        "one line: what's wrong + the fix. Ignore pure style/nits. "
        "If the change is correct and complete for the task, reply with EXACTLY 'NO ISSUES' and nothing else. "
        "Otherwise list at most 5 issues, most important first."
    )
    try:
        from src.llm_core import llm_call_async
        out = await llm_call_async(
            endpoint_url, model, [{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=400, headers=headers or {},
        )
        text = (out or "").strip()
        has = bool(text) and "NO ISSUES" not in text.upper()[:40] and len(text) > 12
        return text, has
    except Exception as exc:
        return f"review_failed: {exc}", False


async def _generate_test(prompt: str, diff: str, mirror_path: str,
                         endpoint_url: str, model: str, headers: dict | None) -> dict:
    """Generate a focused pytest test for the change and write it into the mirror,
    so the authoritative `pytest_changed` check runs it and it ships in the patch.
    Best-effort; returns {generated, test_file?}. Never raises."""
    instr = (
        f"TASK:\n{prompt}\n\nIMPLEMENTATION (unified diff of the change):\n{diff}\n\n"
        "Write a FOCUSED pytest test that verifies the PUBLIC behavior the task asked for: a few "
        "concrete assertions on normal inputs plus one or two edge cases. Import the code by the "
        "real module path shown in the diff (e.g. `from src.foo import bar`). Use plain `assert` in "
        "pytest test functions. Keep it small and CORRECT — do not test private internals or invent "
        "behavior the task didn't specify. Output EXACTLY:\nPATH: tests/test_<name>.py\n"
        "```python\n<test code>\n```"
    )
    try:
        from src.llm_core import llm_call_async
        out = await llm_call_async(endpoint_url, model, [{"role": "user", "content": instr}],
                                   temperature=0.1, max_tokens=700, headers=headers or {})
    except Exception as exc:
        return {"generated": False, "error": str(exc)[:200]}
    import re as _re
    codem = _re.search(r"```(?:python)?\n(.*?)```", out or "", _re.S)
    if not codem:
        return {"generated": False}
    code = codem.group(1).strip()
    pathm = _re.search(r"PATH:\s*([^\n`]+)", out or "")
    rel = (pathm.group(1).strip() if pathm else "tests/test_generated.py").lstrip("/")
    name = Path(rel).name
    if ".." in Path(rel).parts or not (name.startswith("test_") or name.endswith("_test.py")):
        rel = "tests/test_generated.py"
    # Only write a test that at least compiles — a broken generated test would
    # otherwise fail compile-changed and drag the whole build to REVIEW.
    try:
        compile(code, rel, "exec")
    except SyntaxError:
        return {"generated": False, "error": "generated test did not compile"}
    try:
        dest = Path(mirror_path) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        return {"generated": True, "test_file": rel}
    except Exception as exc:
        return {"generated": False, "error": str(exc)[:200]}


async def _review_and_repair(*, prompt, mirror_path, run_id, owner, session_id,
                             endpoint_url, model, headers, d42_tools, root,
                             patch_file, checks_status, changed, max_rounds,
                             status_path=None):
    """Critique the current diff; if real issues are found, repair the change and
    keep the BETTER of original vs repaired (monotonic — repair can only help or
    hold). Returns {patch_file, checks_status, changed, package_status, info}.
    Reused by the single build AND each design-panel candidate."""
    from src.workspace_sandbox_coder import run_sandbox_coding

    info: dict[str, Any] = {"review_repair_applied": False}
    out = {"patch_file": patch_file, "checks_status": checks_status,
           "changed": changed, "package_status": None, "info": info}
    # Surface the review/repair/judge phases in the run status so a multi-minute
    # build isn't an opaque, stale "coding" to the poller. (Derive the tracking id
    # from the status path; only the single build passes one.)
    _tid = Path(status_path).stem if status_path else None

    def _set_state(s: str) -> None:
        if _tid:
            _write_sandbox_status(_tid, {"state": s})

    pre_diff = _read_patch_text(root, patch_file, max_chars=4000)
    if not (pre_diff and changed):
        return out
    _set_state("reviewing")
    issues, has_issues = await _review_diff(prompt, pre_diff, endpoint_url, model, headers)
    info["review_issues"] = (issues or "")[:1500]
    if not has_issues:
        return out

    pre_checks_status, pre_patch_file, pre_changed = checks_status, patch_file, changed
    pre_saved_rel = None
    try:
        if pre_patch_file:
            pre_saved_rel = str(pre_patch_file).replace(".patch", ".pre_repair.patch")
            shutil.copyfile(Path(root) / pre_patch_file, Path(root) / pre_saved_rel)
    except Exception:
        pre_saved_rel = None

    repair_brief = (
        "A code reviewer found these issues in your CURRENT change. Fix each one, "
        "then verify (compile / run the tests). Do not regress what already works.\n\n" + issues
    )
    _set_state("repairing")
    await run_sandbox_coding(
        mirror_path=mirror_path, run_id=run_id, prompt=prompt,
        owner=owner, session_id=session_id,
        endpoint_url=endpoint_url, model=model, headers=headers,
        max_rounds=max(8, max_rounds // 2), status_path=status_path,
        temperature=0.25, extra_brief=repair_brief, state_label="repairing",
    )
    checks, _ = await asyncio.to_thread(
        _run_json, ["python3", str(d42_tools / "run_d42_dev_mirror_checks.py"), "--run-id", run_id], root)
    post_checks_status = (checks or {}).get("status", "UNKNOWN")
    post_hard = (checks or {}).get("hard_failure_count")
    package, _ = await asyncio.to_thread(
        _run_json, ["python3", str(d42_tools / "package_d42_dev_change.py"), "--run-id", run_id], root)
    post_package_status = (package or {}).get("status", "UNKNOWN")
    post_patch_file = (package or {}).get("patch_file")
    post_changed = (package or {}).get("changed_file_count")
    post_diff = _read_patch_text(root, post_patch_file, max_chars=4000)

    # MONOTONIC GUARD — keep the better of {original, repaired}; a checks
    # regression auto-loses, otherwise a 2-way judge decides.
    keep = "repaired"
    if not post_diff or not post_changed:
        keep = "original"
    elif "PASS" in str(pre_checks_status) and "PASS" not in str(post_checks_status):
        keep = "original"
    else:
        _set_state("judging")
        widx, wreason = await _judge_candidates(prompt, [
            {"idx": 1, "label": "original", "checks_status": pre_checks_status,
             "hard_failures": None, "changed": pre_changed, "diff": pre_diff},
            {"idx": 2, "label": "repaired", "checks_status": post_checks_status,
             "hard_failures": post_hard, "changed": post_changed, "diff": post_diff},
        ], endpoint_url, model, headers)
        keep = "original" if widx == 1 else "repaired"
        info["repair_judge_reason"] = (wreason or "")[:300]

    info.update({
        "review_repair_applied": True, "repair_kept": keep,
        "pre_repair_checks_status": pre_checks_status, "pre_repair_changed": pre_changed,
        "pre_repair_diff": pre_diff, "post_repair_diff": post_diff,
    })
    if keep == "repaired":
        out.update({"patch_file": post_patch_file, "checks_status": post_checks_status,
                    "changed": post_changed, "package_status": post_package_status})
    else:
        out.update({"patch_file": pre_saved_rel or pre_patch_file,
                    "checks_status": pre_checks_status, "changed": pre_changed})
    return out


async def execute_sandbox_design_panel(
    *,
    tracking_id: str,
    prompt: str,
    owner: str,
    session_id: str | None,
    endpoint_url: str,
    model: str,
    headers: dict | None = None,
    candidates: int = 3,
    max_rounds: int = 30,
    review_repair: bool = True,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
    root: Path | str = ROOT,
    d42_tools: Path | str = D42_TOOLS,
) -> dict[str, Any]:
    root = Path(root)
    d42_tools = Path(d42_tools)
    queue_dir = Path(queue_dir)
    n = max(2, min(int(candidates or 3), 4))

    _write_sandbox_status(tracking_id, {
        "state": "design_panel", "mode": "design_panel", "candidate_target": n,
        "prompt": str(prompt)[:2000], "owner": owner, "session_id": session_id,
        "created_at": (read_sandbox_status(tracking_id) or {}).get("created_at")
        or datetime.now(timezone.utc).isoformat(),
    })

    created_run_ids: list[str] = []
    try:
        cleanup_stale_mirrors(root)  # backstop before spinning up N more mirrors
        req = create_code_request(
            prompt, "design_panel", queue_dir=queue_dir,
            metadata={"mode": "design_panel", "owner": owner,
                      "session_id": session_id, "tracking_id": tracking_id},
        )
        from src.workspace_sandbox_coder import run_sandbox_coding

        results: list[dict] = []
        for i in range(n):
            label = chr(ord("A") + i)
            _write_sandbox_status(tracking_id, {"state": f"coding_candidate_{label}",
                                                "candidate_index": i + 1})
            d42_req, _ = await asyncio.to_thread(
                _run_json, ["python3", str(d42_tools / "create_d42_dev_request.py"),
                            "--title", f"panel_{label}", "--prompt", prompt], root)
            if not d42_req or d42_req.get("status") != "PASS_D42_DEV_REQUEST_CREATED":
                continue
            d42_mirror, _ = await asyncio.to_thread(
                _run_json, ["python3", str(d42_tools / "create_d42_dev_mirror.py"),
                            "--request-id", d42_req["request_id"]], root)
            if not d42_mirror or d42_mirror.get("status") != "PASS_D42_DEV_MIRROR_CREATED":
                continue
            run_id = d42_mirror["run_id"]
            created_run_ids.append(run_id)
            mirror_path = d42_mirror["mirror_path"]
            # Generate this candidate at higher temperature, steered to a distinct design.
            await run_sandbox_coding(
                mirror_path=mirror_path, run_id=run_id, prompt=prompt,
                owner=owner, session_id=session_id,
                endpoint_url=endpoint_url, model=model, headers=headers,
                max_rounds=max_rounds, temperature=0.85,
                extra_brief=_APPROACH_FRAMINGS[i % len(_APPROACH_FRAMINGS)],
            )
            checks, _ = await asyncio.to_thread(
                _run_json, ["python3", str(d42_tools / "run_d42_dev_mirror_checks.py"),
                            "--run-id", run_id], root)
            package, _ = await asyncio.to_thread(
                _run_json, ["python3", str(d42_tools / "package_d42_dev_change.py"),
                            "--run-id", run_id], root)
            patch_file = (package or {}).get("patch_file")
            changed = (package or {}).get("changed_file_count")
            checks_status = (checks or {}).get("status", "UNKNOWN")
            hard_failures = (checks or {}).get("hard_failure_count")
            # Review-repair EACH candidate (monotonic) before judging — the panel
            # then chooses among polished candidates, not raw first drafts.
            repair_kept = None
            if review_repair and changed:
                _write_sandbox_status(tracking_id, {"state": f"repairing_candidate_{label}"})
                rr = await _review_and_repair(
                    prompt=prompt, mirror_path=mirror_path, run_id=run_id, owner=owner,
                    session_id=session_id, endpoint_url=endpoint_url, model=model, headers=headers,
                    d42_tools=d42_tools, root=root, patch_file=patch_file,
                    checks_status=checks_status, changed=changed, max_rounds=max_rounds,
                )
                patch_file, checks_status, changed = rr["patch_file"], rr["checks_status"], rr["changed"]
                repair_kept = rr["info"].get("repair_kept")
            results.append({
                "idx": i + 1, "label": f"Approach {label}", "run_id": run_id,
                "checks_status": checks_status, "hard_failures": hard_failures,
                "patch_file": patch_file, "changed": changed, "repair_kept": repair_kept,
                "diff": _read_patch_text(root, patch_file),
            })
            _write_sandbox_status(tracking_id, {"candidates_done": len(results)})

        pool = [c for c in results if c.get("changed")] or results
        if not pool:
            return _sandbox_fail(tracking_id, "DESIGN_PANEL_NO_CANDIDATES", {"candidates": len(results)})

        _write_sandbox_status(tracking_id, {"state": "judging"})
        idx, reason = await _judge_candidates(prompt, pool, endpoint_url, model, headers)
        winner = next((c for c in pool if c["idx"] == idx), None)
        if not winner:
            winner = next((c for c in pool if "PASS" in str(c.get("checks_status"))), pool[0])
            reason = (reason or "") + " [fallback: judge unclear; picked a checks-passing candidate]"

        update_code_request_status(req["request_id"], "design_panel_done", queue_dir=queue_dir)
        review_url = f"/workspace/patch-review?patch={winner['patch_file']}" if winner.get("patch_file") else None
        _write_sandbox_status(tracking_id, {
            "state": "done", "mode": "design_panel",
            "candidate_count": len(results),
            "candidates": [{"idx": c["idx"], "label": c["label"],
                            "checks_status": c["checks_status"], "changed": c["changed"],
                            "patch_file": c["patch_file"]} for c in results],
            "winner_index": winner["idx"], "winner_label": winner["label"],
            "judge_reason": reason,
            "checks_status": winner.get("checks_status"),
            "hard_failure_count": winner.get("hard_failures"),
            "patch_file": winner.get("patch_file"),
            "changed_file_count": winner.get("changed"),
            "review_url": review_url,
        })
        logger.info("[sandbox] design panel %s done: %d candidates, winner=%s checks=%s",
                    tracking_id, len(results), winner.get("label"), winner.get("checks_status"))
        return read_sandbox_status(tracking_id) or {}
    except Exception as exc:
        return _sandbox_fail(tracking_id, "ERROR_DESIGN_PANEL", {"error": str(exc)[:500]})
    finally:
        # Every candidate's patch is extracted -> all mirrors are scratch. Drop
        # them on EVERY exit so a failed candidate can't leak the whole panel.
        for rid in created_run_ids:
            remove_mirror(rid, root)
