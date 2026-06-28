from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.workspace_patch_review import review_patch

DEFAULT_AUTH_ENV = "MYAI_WORKSPACE_REVIEW_API_TOKEN"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safety() -> dict[str, bool]:
    return {
        "patch_applied": False,
        "commit_performed": False,
        "push_performed": False,
        "service_restart_performed": False,
        "lan_exposure_allowed": False,
        "model_endpoint_exposure_allowed": False,
        "remote_command_execution_allowed": False,
        "whatsapp_outbound_allowed": False,
    }


def authenticate_request(
    token: str | None,
    *,
    expected_token: str | None = None,
    env_var: str = DEFAULT_AUTH_ENV,
) -> dict[str, Any]:
    configured_token = expected_token if expected_token is not None else os.getenv(env_var)

    result = {
        "authenticated": False,
        "status": "UNKNOWN",
        "env_var": env_var,
        "updated_at": _now(),
    }

    if not configured_token:
        result["status"] = "BLOCKED_AUTH_TOKEN_NOT_CONFIGURED"
        return result

    if not token:
        result["status"] = "BLOCKED_AUTH_TOKEN_MISSING"
        return result

    import hmac
    if not hmac.compare_digest(str(token), str(configured_token)):
        result["status"] = "BLOCKED_AUTH_TOKEN_MISMATCH"
        return result

    result["authenticated"] = True
    result["status"] = "PASS_AUTHENTICATED"
    return result


def _read_patch_preview(patch_file: str | Path, max_lines: int = 80) -> str:
    path = Path(patch_file)
    if not path.exists():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[:max_lines])


def _call_review_patch(
    patch_file: str | Path,
    *,
    root: str | Path,
    allowed_prefixes: list[str] | None,
) -> dict[str, Any]:
    sig = inspect.signature(review_patch)
    kwargs: dict[str, Any] = {}

    for name, param in sig.parameters.items():
        lname = name.lower()

        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        if ("patch" in lname and "path" in lname) or lname in {"patch", "patch_file", "diff", "diff_path"}:
            kwargs[name] = patch_file
        elif lname in {"root", "repo_root", "repository", "repo", "cwd", "worktree", "worktree_path"}:
            kwargs[name] = root
        elif "allowed" in lname and "prefix" in lname:
            kwargs[name] = allowed_prefixes
        elif "prefix" in lname and "allowed" in lname:
            kwargs[name] = allowed_prefixes
        elif param.default is not inspect._empty:
            continue
        else:
            raise TypeError(f"Cannot safely supply required parameter {name!r} for review_patch")

    result = review_patch(**kwargs)
    if isinstance(result, dict):
        return result
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"raw_result_repr": repr(result)}


def review_patch_api(
    patch_file: str | Path,
    *,
    token: str | None,
    expected_token: str | None = None,
    root: str | Path = ".",
    allowed_prefixes: list[str] | None = None,
    include_preview: bool = True,
) -> dict[str, Any]:
    auth = authenticate_request(token, expected_token=expected_token)

    result: dict[str, Any] = {
        "status": "UNKNOWN",
        "authenticated": auth["authenticated"],
        "auth": auth,
        "patch_file": str(patch_file),
        "root": str(root),
        "allowed_prefixes": allowed_prefixes,
        "safety": _safety(),
        "updated_at": _now(),
    }

    if not auth["authenticated"]:
        result["status"] = auth["status"]
        return result

    review = _call_review_patch(
        patch_file,
        root=root,
        allowed_prefixes=allowed_prefixes,
    )

    result["review"] = review
    result["review_status"] = review.get("status")

    if include_preview:
        result["patch_preview_first_80_lines"] = _read_patch_preview(patch_file, 80)

    result["status"] = (
        "PASS_PATCH_REVIEW_API"
        if review.get("status") == "PASS_PATCH_REVIEW"
        else "REVIEW_PATCH_REVIEW_API"
    )
    return result


def list_workspace_requests_api(
    requests_dir: str | Path,
    *,
    token: str | None,
    expected_token: str | None = None,
    include_payload: bool = False,
    limit: int = 100,
) -> dict[str, Any]:
    auth = authenticate_request(token, expected_token=expected_token)

    result: dict[str, Any] = {
        "status": "UNKNOWN",
        "authenticated": auth["authenticated"],
        "auth": auth,
        "requests_dir": str(requests_dir),
        "include_payload": include_payload,
        "limit": limit,
        "safety": _safety(),
        "updated_at": _now(),
    }

    if not auth["authenticated"]:
        result["status"] = auth["status"]
        result["requests"] = []
        return result

    path = Path(requests_dir)
    if not path.exists():
        result["status"] = "PASS_WORKSPACE_REQUESTS_LIST_EMPTY"
        result["requests"] = []
        return result

    requests: list[dict[str, Any]] = []
    for file_path in sorted(path.glob("*.json"), reverse=True)[:limit]:
        item: dict[str, Any] = {
            "file": str(file_path),
            "name": file_path.name,
        }

        if include_payload:
            try:
                payload = json.loads(file_path.read_text(errors="replace"))
            except Exception as exc:
                payload = {"error": repr(exc)}
            item["payload"] = payload

        requests.append(item)

    result["requests"] = requests
    result["request_count"] = len(requests)
    result["status"] = "PASS_WORKSPACE_REQUESTS_LISTED"
    return result
