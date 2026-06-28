"""Local workspace code-request queue for my.ai / Odysseus.

Filesystem-backed queue for code-work requests. Safe-by-default:
no live repo modification, commits, pushes, service restarts, remote command
execution, LAN exposure, model endpoint exposure, or WhatsApp outbound.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
from typing import Any


# Resolve the repo root from this file's location so it is correct both on the
# host (/home/youruser/odysseus) and inside the app container (/app). The old
# hardcoded host path existed in-container too but as root:root, so the app
# process (uid 1000) got "permission denied" writing the request queue — only
# masked until a non-root caller (the unblocked myai build/panel CLI) hit it.
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_DIR = DEFAULT_ROOT / "data/workspace/requests"


DEFAULT_SAFETY: dict[str, bool] = {
    "live_repo_modification_allowed": False,
    "commit_allowed": False,
    "push_allowed": False,
    "service_restart_allowed": False,
    "remote_command_execution_allowed": False,
    "lan_exposure_allowed": False,
    "model_endpoint_exposure_allowed": False,
    "whatsapp_outbound_allowed": False,
}


@dataclass(frozen=True)
class CodeRequest:
    request_id: str
    title: str
    prompt: str
    status: str
    created_at: str
    safety: dict[str, bool]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "title": self.title,
            "prompt": self.prompt,
            "status": self.status,
            "created_at": self.created_at,
            "safety": dict(self.safety),
            "metadata": dict(self.metadata),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower()).strip("_")
    return slug[:48] or "code_request"


def _make_request_id(title: str, prompt: str, created_at: str) -> str:
    seed = f"{created_at}\n{title}\n{prompt}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:10]
    parsed = datetime.fromisoformat(created_at)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    stamp = parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"wcr_{stamp}_{_slugify_title(title)}_{digest}"


def _safe_json_path(queue_dir: Path, request_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", request_id):
        raise ValueError(f"Invalid request_id: {request_id!r}")
    return queue_dir / f"{request_id}.json"


def create_code_request(
    prompt: str,
    title: str = "code_request",
    *,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
    metadata: dict[str, Any] | None = None,
    safety: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Create and persist a local code-work request."""
    prompt = str(prompt).strip()
    title = str(title).strip() or "code_request"

    if not prompt:
        raise ValueError("prompt is required")

    queue_path = Path(queue_dir)
    queue_path.mkdir(parents=True, exist_ok=True)

    created_at = _utc_now()
    request_id = _make_request_id(title, prompt, created_at)

    merged_safety = dict(DEFAULT_SAFETY)
    if safety:
        for key, value in safety.items():
            merged_safety[str(key)] = bool(value)

    payload = CodeRequest(
        request_id=request_id,
        title=title,
        prompt=prompt,
        status="queued",
        created_at=created_at,
        safety=merged_safety,
        metadata=dict(metadata or {}),
    ).to_dict()

    out = _safe_json_path(queue_path, request_id)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_code_request(request_id: str, *, queue_dir: Path | str = DEFAULT_QUEUE_DIR) -> dict[str, Any]:
    """Read one queued code-work request by request_id."""
    path = _safe_json_path(Path(queue_dir), str(request_id))
    if not path.exists():
        raise FileNotFoundError(f"Code request not found: {request_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_code_requests(
    *,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List queued code-work requests, newest first by created_at."""
    queue_path = Path(queue_dir)
    if not queue_path.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in queue_path.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status is not None and payload.get("status") != status:
            continue
        items.append(payload)

    items.sort(key=lambda item: (item.get("created_at") or "", item.get("request_id") or ""), reverse=True)
    safe_limit = max(0, int(limit))
    return items[:safe_limit]


def update_code_request_status(
    request_id: str,
    status: str,
    *,
    queue_dir: Path | str = DEFAULT_QUEUE_DIR,
) -> dict[str, Any]:
    """Update the status of a queued code-work request."""
    clean_status = str(status).strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]+", clean_status):
        raise ValueError(f"Invalid status: {status!r}")

    queue_path = Path(queue_dir)
    payload = read_code_request(str(request_id), queue_dir=queue_path)
    payload["status"] = clean_status
    payload["updated_at"] = _utc_now()

    out = _safe_json_path(queue_path, str(request_id))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
