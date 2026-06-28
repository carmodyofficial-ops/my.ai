"""Explicit patch approval/apply helper for my.ai / Odysseus.

This module is intentionally local and conservative. It can apply a patch only
after:
- an exact approval phrase is provided,
- patch review passes,
- git apply --check passes,
- optional allowed-prefix scope is satisfied.

It never commits, pushes, restarts services, exposes endpoints, or enables
WhatsApp outbound.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from .workspace_patch_review import review_patch


# Resolve from this file's location so it is correct on the host AND in-container
# (/app); the old hardcoded host path broke the app-user apply (same bug as the
# request queue).
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVAL_PHRASE = "APPROVE_APPLY_REVIEWED_PATCH"

# When no explicit scope is given, confine the apply to the code dirs sandbox
# builds actually touch — fail-closed instead of allowing a repo-wide change.
_DEFAULT_APPLY_SCOPE = [
    "src/", "tests/", "routes/", "services/", "core/", "scripts/",
    "static/", "templates/", "data/d42_tools/",
]


APPROVAL_SAFETY = {
    "commit_performed": False,
    "push_performed": False,
    "service_restart_performed": False,
    "remote_command_execution_allowed": False,
    "lan_exposure_allowed": False,
    "model_endpoint_exposure_allowed": False,
    "whatsapp_outbound_allowed": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_pre_apply_backup(root_path: Path) -> dict[str, Any]:
    """Best-effort restore point captured right before ``git apply``.

    Records the current HEAD sha and saves the working-tree diff to
    ``data/workspace/backups/<ts>.pre_apply.diff`` so an applied patch can be
    undone if needed (auto-generated sandbox patches make this materially more
    important than when patches were always empty). Never raises — a backup
    failure must not block a properly-approved apply, but it is reported.
    """
    info: dict[str, Any] = {"created_at": _utc_now(), "head": None, "pre_apply_diff": None}
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root_path),
            text=True, capture_output=True, timeout=30,
        )
        info["head"] = (head.stdout or "").strip() or None
    except Exception:
        pass
    try:
        backups = root_path / "data/workspace/backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        diff = subprocess.run(
            ["git", "diff"], cwd=str(root_path),
            text=True, capture_output=True, timeout=60,
        )
        backup_path = backups / f"{stamp}.pre_apply.diff"
        backup_path.write_text(diff.stdout or "", encoding="utf-8")
        info["pre_apply_diff"] = str(backup_path)
    except Exception:
        pass
    return info


def _post_apply_check(root_path: Path, changed_files: list[str]) -> dict[str, Any]:
    """After applying to the LIVE tree, byte-compile the changed Python files. The
    mirror was a point-in-time copy; live may have drifted, so a patch that passed
    in the sandbox can still break live (a syntax-level conflict). Cheap guard."""
    py = [f for f in (changed_files or []) if f.endswith(".py")]
    if not py:
        return {"checked": [], "ok": True}
    try:
        res = subprocess.run(["python3", "-m", "py_compile", *py], cwd=str(root_path),
                             text=True, capture_output=True, timeout=120)
        return {"checked": py, "ok": res.returncode == 0,
                "returncode": res.returncode, "stderr": (res.stderr or "")[-2000:]}
    except Exception as exc:
        return {"checked": py, "ok": False, "error": str(exc)[:200]}


def apply_reviewed_patch(
    patch_file: str | Path,
    *,
    approval_phrase: str,
    required_approval_phrase: str = DEFAULT_APPROVAL_PHRASE,
    root: str | Path = ROOT,
    allowed_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Review and apply a patch only with exact explicit approval."""
    root_path = Path(root)
    patch_path = Path(patch_file)
    if not patch_path.is_absolute():
        patch_path = root_path / patch_path

    import hmac
    if not hmac.compare_digest(str(approval_phrase), str(required_approval_phrase)):
        return {
            "status": "BLOCKED_APPROVAL_PHRASE_MISMATCH",
            "updated_at": _utc_now(),
            "patch_file": str(patch_path),
            "patch_applied": False,
            "review": None,
            "safety": dict(APPROVAL_SAFETY),
        }

    # Fail closed: an empty scope used to allow a repo-wide change; default to the
    # code dirs sandbox builds touch.
    allowed_prefixes = allowed_prefixes or _DEFAULT_APPLY_SCOPE
    review = review_patch(patch_path, root=root_path, allowed_prefixes=allowed_prefixes)

    if review.get("status") != "PASS_PATCH_REVIEW":
        return {
            "status": "BLOCKED_PATCH_REVIEW_NOT_PASS",
            "updated_at": _utc_now(),
            "patch_file": str(patch_path),
            "patch_applied": False,
            "review": review,
            "safety": dict(APPROVAL_SAFETY),
        }

    # Capture a restore point before mutating the working tree.
    backup = _create_pre_apply_backup(root_path)

    apply_result = subprocess.run(
        ["git", "apply", str(patch_path)],
        cwd=str(root_path),
        text=True,
        capture_output=True,
        timeout=300,
    )

    applied = apply_result.returncode == 0

    # Post-apply: verify on the LIVE tree. If the applied patch breaks live
    # (drift since the mirror snapshot), revert it so we never leave the working
    # tree broken — the human approved a change that builds, not a half-apply.
    post_check = None
    reverted = False
    if applied:
        post_check = _post_apply_check(root_path, review.get("changed_files", []))
        if not post_check.get("ok"):
            rev = subprocess.run(["git", "apply", "-R", str(patch_path)], cwd=str(root_path),
                                 text=True, capture_output=True, timeout=300)
            reverted = rev.returncode == 0

    ok = applied and (post_check is None or post_check.get("ok"))
    if ok:
        status = "PASS_REVIEWED_PATCH_APPLIED"
    elif not applied:
        status = "FAIL_GIT_APPLY"
    elif reverted:
        status = "REVERTED_POST_APPLY_CHECK_FAILED"
    else:
        status = "FAIL_POST_APPLY_CHECK_NOT_REVERTED"
    return {
        "status": status,
        "updated_at": _utc_now(),
        "patch_file": str(patch_path),
        "patch_applied": ok,  # False if it was applied then reverted
        "changed_files": review.get("changed_files", []),
        "review": review,
        "backup": backup,
        "post_apply_check": post_check,
        "reverted": reverted,
        "git_apply": {
            "returncode": apply_result.returncode,
            "stdout": apply_result.stdout[-8000:],
            "stderr": apply_result.stderr[-8000:],
        },
        "safety": dict(APPROVAL_SAFETY),
    }
