from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_COMMIT_APPROVAL_PHRASE = "APPROVE_CREATE_LOCAL_COMMIT"


def _run(cmd: list[str], root: Path) -> dict[str, Any]:
    p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
    return {
        "cmd": cmd,
        "cwd": str(root),
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def _safety(patch_applied: bool = False, commit_performed: bool = False) -> dict[str, bool]:
    return {
        "patch_applied": patch_applied,
        "commit_performed": commit_performed,
        "push_performed": False,
        "service_restart_performed": False,
        "lan_exposure_allowed": False,
        "model_endpoint_exposure_allowed": False,
        "remote_command_execution_allowed": False,
        "whatsapp_outbound_allowed": False,
    }


def _status_paths(status_stdout: str) -> list[str]:
    paths: list[str] = []
    for raw in status_stdout.splitlines():
        if not raw:
            continue
        path = raw[3:] if len(raw) > 3 else raw
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return sorted(set(paths))


def _within_allowed(path: str, allowed_prefixes: list[str] | None) -> bool:
    if not allowed_prefixes:
        return True
    normalized = path.replace("\\", "/")
    for prefix in allowed_prefixes:
        clean = prefix.replace("\\", "/")
        if normalized == clean or normalized.startswith(clean.rstrip("/") + "/"):
            return True
    return False


def create_reviewed_commit(
    paths: list[str],
    *,
    commit_message: str,
    approval_phrase: str,
    required_approval_phrase: str = DEFAULT_COMMIT_APPROVAL_PHRASE,
    root: str | Path = ".",
    allowed_prefixes: list[str] | None = None,
    tests_passed: bool = False,
    require_tests_passed: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    repo_root = Path(root)
    updated_at = datetime.now(timezone.utc).isoformat()

    result: dict[str, Any] = {
        "status": "UNKNOWN",
        "root": str(repo_root),
        "paths": list(paths),
        "commit_message": commit_message,
        "allowed_prefixes": allowed_prefixes,
        "tests_passed": tests_passed,
        "require_tests_passed": require_tests_passed,
        "dry_run": dry_run,
        "commit_performed": False,
        "safety": _safety(commit_performed=False),
        "updated_at": updated_at,
    }

    if approval_phrase != required_approval_phrase:
        result["status"] = "BLOCKED_COMMIT_APPROVAL_PHRASE_MISMATCH"
        return result

    if require_tests_passed and not tests_passed:
        result["status"] = "BLOCKED_TESTS_NOT_PASSED"
        return result

    if not commit_message or not commit_message.strip():
        result["status"] = "BLOCKED_EMPTY_COMMIT_MESSAGE"
        return result

    if not paths:
        result["status"] = "BLOCKED_NO_COMMIT_PATHS"
        return result

    status = _run(["git", "status", "--porcelain"], repo_root)
    result["git_status"] = status

    if status["returncode"] != 0:
        result["status"] = "REVIEW_GIT_STATUS_FAILED"
        return result

    changed_paths = _status_paths(status["stdout"])
    result["changed_paths"] = changed_paths

    if not changed_paths:
        result["status"] = "BLOCKED_NO_CHANGES_TO_COMMIT"
        return result

    unexpected_paths = [
        path for path in changed_paths
        if not _within_allowed(path, allowed_prefixes)
    ]
    result["unexpected_paths"] = unexpected_paths

    if unexpected_paths:
        result["status"] = "BLOCKED_UNEXPECTED_DIRTY_PATHS"
        return result

    requested_paths = sorted(set(str(Path(p)).replace("\\", "/") for p in paths))
    result["requested_paths"] = requested_paths

    requested_outside_allowed = [
        path for path in requested_paths
        if not _within_allowed(path, allowed_prefixes)
    ]
    result["requested_paths_outside_allowed_prefixes"] = requested_outside_allowed

    if requested_outside_allowed:
        result["status"] = "BLOCKED_REQUESTED_PATH_OUTSIDE_ALLOWED_PREFIXES"
        return result

    missing_requested_changes = [
        path for path in requested_paths
        if path not in changed_paths
    ]
    result["missing_requested_changes"] = missing_requested_changes

    if missing_requested_changes:
        result["status"] = "BLOCKED_REQUESTED_PATHS_NOT_DIRTY"
        return result

    if dry_run:
        result["status"] = "PASS_COMMIT_GATE_DRY_RUN"
        return result

    add_result = _run(["git", "add", "--", *requested_paths], repo_root)
    result["git_add"] = add_result

    if add_result["returncode"] != 0:
        result["status"] = "REVIEW_GIT_ADD_FAILED"
        return result

    commit_result = _run(["git", "commit", "-m", commit_message], repo_root)
    result["git_commit"] = commit_result

    if commit_result["returncode"] != 0:
        result["status"] = "REVIEW_GIT_COMMIT_FAILED"
        return result

    result["status"] = "PASS_REVIEWED_LOCAL_COMMIT_CREATED"
    result["commit_performed"] = True
    result["safety"] = _safety(commit_performed=True)
    return result
