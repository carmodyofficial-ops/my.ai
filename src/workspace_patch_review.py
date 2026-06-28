"""Patch review helpers for my.ai / Odysseus.

This module reviews generated patch files without applying them.
It is intentionally safe-by-default:

- parses changed files from unified diff headers
- runs git apply --check only
- produces JSON-serializable review reports
- never applies patches, commits, pushes, restarts services, exposes endpoints,
  or enables WhatsApp outbound
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import subprocess
from typing import Any


ROOT = Path("/home/youruser/odysseus")


REVIEW_SAFETY = {
    "patch_applied": False,
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


def parse_changed_files_from_patch_text(patch_text: str) -> list[str]:
    """Return sorted changed files from unified diff text — additions, modifications,
    DELETIONS (`+++ /dev/null`, real path on the `--- a/` side) and RENAMES/COPIES
    (`diff --git` + `rename/copy` headers). Parsing only `+++ b/` let a patch delete
    or move files outside the approved scope, since those paths never appear there."""
    files = set()

    def _add(value: str) -> None:
        value = (value or "").strip()
        if value and value != "/dev/null":
            files.add(value)

    for match in re.finditer(r"^\+\+\+\s+b/(.+)$", patch_text, flags=re.MULTILINE):
        _add(match.group(1))
    for match in re.finditer(r"^---\s+a/(.+)$", patch_text, flags=re.MULTILINE):
        _add(match.group(1))  # source side — catches deletions
    for match in re.finditer(r"^diff --git a/(.+?) b/(.+)$", patch_text, flags=re.MULTILINE):
        _add(match.group(1)); _add(match.group(2))
    for match in re.finditer(r"^(?:rename|copy) (?:from|to) (.+)$", patch_text, flags=re.MULTILINE):
        _add(match.group(1))
    return sorted(files)


def review_patch(
    patch_file: str | Path,
    *,
    root: str | Path = ROOT,
    allowed_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Review a patch without applying it."""
    root_path = Path(root)
    patch_path = Path(patch_file)
    if not patch_path.is_absolute():
        patch_path = root_path / patch_path

    if not patch_path.exists():
        return {
            "status": "FAIL_PATCH_MISSING",
            "patch_file": str(patch_path),
            "changed_files": [],
            "git_apply_check_ok": False,
            "safety": dict(REVIEW_SAFETY),
        }

    patch_text = patch_path.read_text(errors="replace")
    changed_files = parse_changed_files_from_patch_text(patch_text)

    allowed_prefixes = allowed_prefixes or []
    unexpected_files = []
    if allowed_prefixes:
        unexpected_files = [
            file for file in changed_files
            if not any(file == prefix or file.startswith(prefix.rstrip("/") + "/") for prefix in allowed_prefixes)
        ]

    apply_check = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=str(root_path),
        text=True,
        capture_output=True,
        timeout=300,
    )

    status = "PASS_PATCH_REVIEW"
    if unexpected_files:
        status = "REVIEW_PATCH_SCOPE"
    if apply_check.returncode != 0:
        status = "REVIEW_PATCH_APPLY_CHECK"

    return {
        "status": status,
        "updated_at": _utc_now(),
        "patch_file": str(patch_path),
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "allowed_prefixes": allowed_prefixes,
        "unexpected_files": unexpected_files,
        "git_apply_check_ok": apply_check.returncode == 0,
        "git_apply_check": {
            "returncode": apply_check.returncode,
            "stdout": apply_check.stdout[-8000:],
            "stderr": apply_check.stderr[-8000:],
        },
        "patch_preview_first_120_lines": "\n".join(patch_text.splitlines()[:120]),
        "safety": dict(REVIEW_SAFETY),
    }


def write_patch_review_report(
    patch_file: str | Path,
    output_file: str | Path,
    *,
    root: str | Path = ROOT,
    allowed_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Review a patch and write the review report to JSON."""
    report = review_patch(patch_file, root=root, allowed_prefixes=allowed_prefixes)
    out = Path(output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
