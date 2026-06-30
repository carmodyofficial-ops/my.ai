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


def _run_git(args: list[str], root_path: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(root_path), text=True,
                          capture_output=True, timeout=timeout)


def _git_commit_workflow(
    root_path: Path,
    changed_files: list[str],
    *,
    branch: str | None,
    message: str,
    push: bool,
    open_pr: bool,
    pr_base: str,
) -> dict[str, Any]:
    """Branch (optional) + commit the just-applied change, optionally push +
    open a PR. Strictly opt-in (only reached when the caller passes commit=True
    AND the approval phrase already matched). Scoped ``git add`` of the patch's
    changed files only — never ``git add .``. Never raises: every git/gh failure
    is captured and returned so a commit problem can't crash the apply path.
    """
    out: dict[str, Any] = {
        "branch": None, "branch_created": False, "committed": False,
        "commit_sha": None, "pushed": False, "pr_url": None, "errors": [],
    }
    try:
        # 1. Optional branch-per-task (keeps auto-applied changes off the main
        #    branch). `git switch -c` with a checkout fallback for old git.
        if branch:
            sw = _run_git(["switch", "-c", branch], root_path)
            if sw.returncode != 0:
                sw = _run_git(["checkout", "-b", branch], root_path)
            if sw.returncode != 0:
                out["errors"].append(f"branch: {(sw.stderr or sw.stdout)[-300:]}")
                return out  # don't commit onto an unexpected branch
            out["branch"] = branch
            out["branch_created"] = True
        else:
            cur = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root_path)
            out["branch"] = (cur.stdout or "").strip() or None

        # 2. Stage ONLY the patch's changed files, then commit.
        files = [f for f in (changed_files or []) if isinstance(f, str) and f.strip()]
        if files:
            add = _run_git(["add", "--", *files], root_path)
        else:
            add = _run_git(["add", "-u"], root_path)  # tracked-only fallback
        if add.returncode != 0:
            out["errors"].append(f"add: {(add.stderr or add.stdout)[-300:]}")
            return out
        commit = _run_git(["commit", "-m", message], root_path, timeout=120)
        if commit.returncode != 0:
            out["errors"].append(f"commit: {(commit.stderr or commit.stdout)[-300:]}")
            return out
        out["committed"] = True
        sha = _run_git(["rev-parse", "HEAD"], root_path)
        out["commit_sha"] = (sha.stdout or "").strip()[:40] or None

        # 3. Optional push + PR (needs a remote + auth / gh; default off).
        if push and out["branch"]:
            pr = _run_git(["push", "-u", "origin", out["branch"]], root_path, timeout=180)
            out["pushed"] = pr.returncode == 0
            if pr.returncode != 0:
                out["errors"].append(f"push: {(pr.stderr or pr.stdout)[-300:]}")
            elif open_pr:
                try:
                    gh = subprocess.run(
                        ["gh", "pr", "create", "--base", pr_base, "--head", out["branch"],
                         "--title", message.splitlines()[0][:120], "--body", message],
                        cwd=str(root_path), text=True, capture_output=True, timeout=120)
                    if gh.returncode == 0:
                        _lines = (gh.stdout or "").strip().splitlines()
                        out["pr_url"] = _lines[-1] if _lines else None
                    else:
                        out["errors"].append(f"gh pr: {(gh.stderr or gh.stdout)[-300:]}")
                except Exception as ge:  # gh absent / failed
                    out["errors"].append(f"gh pr: {str(ge)[:200]}")
    except Exception as exc:
        out["errors"].append(f"workflow: {str(exc)[:200]}")
    return out


def apply_reviewed_patch(
    patch_file: str | Path,
    *,
    approval_phrase: str,
    required_approval_phrase: str = DEFAULT_APPROVAL_PHRASE,
    root: str | Path = ROOT,
    allowed_prefixes: list[str] | None = None,
    commit: bool = False,
    branch: str | None = None,
    commit_message: str | None = None,
    push: bool = False,
    open_pr: bool = False,
    pr_base: str = "dev",
) -> dict[str, Any]:
    """Review and apply a patch only with exact explicit approval.

    By default the change is left UNCOMMITTED in the working tree (the
    conservative original behavior). When ``commit=True`` (opt-in, on top of the
    already-required approval phrase), the applied change is branched (if
    ``branch`` is given) and committed; ``push``/``open_pr`` additionally publish
    it. The git workflow is best-effort and never crashes the apply.
    """
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

    # Opt-in git workflow: only when the apply genuinely succeeded AND the caller
    # explicitly asked to commit (on top of the already-matched approval phrase).
    # Reflect what actually happened in a per-call safety copy.
    git_workflow = None
    safety = dict(APPROVAL_SAFETY)
    if ok and commit:
        msg = commit_message or f"Apply reviewed sandbox patch {patch_path.name}"
        git_workflow = _git_commit_workflow(
            root_path, review.get("changed_files", []),
            branch=branch, message=msg, push=push, open_pr=open_pr, pr_base=pr_base,
        )
        safety["commit_performed"] = bool(git_workflow.get("committed"))
        safety["push_performed"] = bool(git_workflow.get("pushed"))

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
        "git_workflow": git_workflow,
        "safety": safety,
    }
