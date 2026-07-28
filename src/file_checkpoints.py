"""Pre-edit checkpoints — per-turn undo for the agent's file changes.

Industry-standard coding agents snapshot a file before they modify it and expose
a user-facing rewind. This system had all the pieces (a pre-apply backup and a
`git apply -R` auto-revert) quarantined inside the sandbox-patch pipeline, so a
user editing through chat or cowork had **no way to undo a turn** — the original
content existed only inside a truncated display diff.

This module is the missing live-path half:

  * `snapshot(path, tool)` is called by every mutating file tool BEFORE it
    writes. It records the previous bytes (or "did not exist", so undo means
    delete) under the session's checkpoint directory.
  * Checkpoints are grouped per agent turn (`begin_group`), so "undo that" can
    revert an entire multi-file change rather than one edit of five.
  * `restore()` / `restore_group()` put the old content back.

Bounded on purpose: files above `MAX_SNAPSHOT_BYTES` are recorded as
un-restorable rather than silently copied, per-session history is capped, and
old session directories are pruned. Nothing here may ever raise into a tool —
a checkpoint failure must not block a legitimate edit, so `snapshot` is
fail-open and only *reduces* what undo can offer.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024      # 2 MB — above this we record metadata only
MAX_CHECKPOINTS_PER_SESSION = 300
MAX_SESSION_DIRS = 24

_active_group: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "agent_checkpoint_group", default=None,
)


def _root() -> str:
    from src.constants import DATA_DIR
    return os.path.join(DATA_DIR, "checkpoints")


def _safe(name: str) -> str:
    """Filesystem-safe bucket name for a session id."""
    keep = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(name or ""))
    return (keep or "default")[:80]


def _session_dir(session_id: Optional[str], create: bool = False) -> str:
    d = os.path.join(_root(), _safe(session_id or "default"))
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def _enabled() -> bool:
    try:
        from src.settings import get_setting
        return bool(get_setting("agent_edit_checkpoints", True))
    except Exception:
        return True


def begin_group(session_id: Optional[str] = None) -> str:
    """Start a new checkpoint group (one agent turn). Returns the group id."""
    gid = f"g{int(time.time())}-{uuid.uuid4().hex[:6]}"
    _active_group.set(gid)
    return gid


def current_group() -> Optional[str]:
    return _active_group.get()


def _prune_sessions() -> None:
    try:
        root = _root()
        if not os.path.isdir(root):
            return
        entries = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isdir(p):
                entries.append((os.path.getmtime(p), p))
        entries.sort(reverse=True)
        import shutil
        for _, p in entries[MAX_SESSION_DIRS:]:
            shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def _prune_session(d: str) -> None:
    try:
        files = sorted(
            (f for f in os.listdir(d) if f.endswith(".json")),
        )
        for f in files[:-MAX_CHECKPOINTS_PER_SESSION] if len(files) > MAX_CHECKPOINTS_PER_SESSION else []:
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass
    except OSError:
        pass


def snapshot(path: str, tool: str = "", session_id: Optional[str] = None) -> Optional[str]:
    """Record the current state of *path* before it is modified.

    Returns a checkpoint id, or None when checkpointing is off or unavailable.
    Never raises — a snapshot failure must not block the edit.
    """
    if not path or not _enabled():
        return None
    try:
        from src.file_ledger import current_session
        sid = session_id or current_session()
        d = _session_dir(sid, create=True)
        existed = os.path.isfile(path)
        content: Optional[str] = None
        too_large = False
        if existed:
            try:
                size = os.path.getsize(path)
                if size > MAX_SNAPSHOT_BYTES:
                    too_large = True
                else:
                    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
                        content = f.read()
            except OSError:
                return None
        cid = f"{int(time.time() * 1000):013d}-{uuid.uuid4().hex[:8]}"
        rec = {
            "id": cid,
            "group": _active_group.get() or "ungrouped",
            "session": sid or "default",
            "path": os.path.realpath(path),
            "tool": tool,
            "ts": time.time(),
            "existed": existed,
            "too_large": too_large,
            "content": content,
            "restored": False,
        }
        tmp = os.path.join(d, f".{cid}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        os.replace(tmp, os.path.join(d, f"{cid}.json"))
        _prune_session(d)
        _prune_sessions()
        return cid
    except Exception:
        logger.debug("[checkpoint] snapshot skipped", exc_info=True)
        return None


def _load(d: str, cid: str) -> Optional[Dict[str, Any]]:
    try:
        with open(os.path.join(d, f"{cid}.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _save(d: str, rec: Dict[str, Any]) -> None:
    try:
        tmp = os.path.join(d, f".{rec['id']}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        os.replace(tmp, os.path.join(d, f"{rec['id']}.json"))
    except OSError:
        pass


def list_checkpoints(session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Most-recent-first checkpoint metadata (without file contents)."""
    out: List[Dict[str, Any]] = []
    try:
        d = _session_dir(session_id)
        if not os.path.isdir(d):
            return []
        for name in sorted(os.listdir(d), reverse=True):
            if not name.endswith(".json") or name.startswith("."):
                continue
            rec = _load(d, name[:-5])
            if not rec:
                continue
            out.append({
                "id": rec.get("id"), "group": rec.get("group"),
                "path": rec.get("path"), "tool": rec.get("tool"),
                "ts": rec.get("ts"), "existed": rec.get("existed"),
                "too_large": rec.get("too_large"), "restored": rec.get("restored"),
                "restorable": bool(not rec.get("too_large")),
            })
            if len(out) >= max(1, limit):
                break
    except OSError:
        return out
    return out


def _restore_record(d: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Put a single checkpoint's content back on disk."""
    path = rec.get("path") or ""
    if rec.get("too_large"):
        return {"ok": False, "path": path,
                "error": "snapshot was too large to store; cannot undo this one"}
    # Re-validate the path at restore time — the allowlist/deny rules may have
    # changed since the edit, and restore is a user-triggered host write.
    try:
        from src.tool_execution import _resolve_tool_path
        path = _resolve_tool_path(path)
    except ValueError as e:
        return {"ok": False, "path": path, "error": str(e)}
    except Exception:
        pass
    try:
        if not rec.get("existed"):
            # The edit CREATED this file — undo means remove it again.
            if os.path.isfile(path):
                os.remove(path)
            action = "deleted"
        else:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(rec.get("content") or "")
            action = "restored"
    except OSError as e:
        return {"ok": False, "path": path, "error": str(e)}
    rec["restored"] = True
    _save(d, rec)
    # The file no longer matches what the agent last read; drop the ledger stamp
    # so the next edit is correctly told to re-read instead of clobbering.
    try:
        from src.file_ledger import forget
        forget(path)
    except Exception:
        pass
    return {"ok": True, "path": path, "action": action}


def restore(checkpoint_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Undo a single checkpoint."""
    d = _session_dir(session_id)
    rec = _load(d, checkpoint_id)
    if not rec:
        return {"ok": False, "error": "checkpoint not found"}
    return _restore_record(d, rec)


def restore_group(group_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Undo every checkpoint in a group (one agent turn), newest first.

    Newest-first matters: if a turn edited the same file twice, replaying the
    oldest snapshot last leaves the file at its true pre-turn state.
    """
    d = _session_dir(session_id)
    if not os.path.isdir(d):
        return {"ok": False, "error": "no checkpoints for this session"}
    recs = []
    for name in sorted(os.listdir(d), reverse=True):
        if not name.endswith(".json") or name.startswith("."):
            continue
        rec = _load(d, name[:-5])
        if rec and rec.get("group") == group_id:
            recs.append(rec)
    if not recs:
        return {"ok": False, "error": "no checkpoints in that group"}
    results = [_restore_record(d, r) for r in recs]
    return {
        "ok": all(r.get("ok") for r in results),
        "group": group_id,
        "restored": [r for r in results if r.get("ok")],
        "failed": [r for r in results if not r.get("ok")],
    }


def latest_group(session_id: Optional[str] = None) -> Optional[str]:
    """Group id of the most recent checkpoint, or None."""
    items = list_checkpoints(session_id, limit=1)
    return items[0].get("group") if items else None
