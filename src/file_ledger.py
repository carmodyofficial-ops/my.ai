"""Per-session file read-ledger — read-before-edit + stale-write protection.

Industry-standard coding agents (Claude Code, Cursor) enforce two mechanical
rules that prompt text alone cannot guarantee:

  1. READ BEFORE EDIT — refuse to modify an existing file the agent has not
     read in this session. Without it, `write_file` silently truncates and
     overwrites a file the model never opened, destroying content it never saw.
  2. STALE-WRITE PROTECTION — refuse to modify a file that changed on disk
     since the agent last read it. Without it, the agent clobbers edits made
     concurrently by the user, another agent, or a `bash` command.

Both failures are silent and destructive, which is why they are enforced here
in the tool layer rather than asked for in the system prompt.

Design notes:
  * Scope is the SESSION, bound via a contextvar in `execute_tool_block` (the
    same pattern as the active workspace) so tools need no signature change.
  * Freshness is checked with a cheap (mtime_ns, size) fast path, falling back
    to a SHA-256 comparison only when those differ — so a rewrite that restores
    identical bytes is correctly treated as unchanged.
  * Successful writes RE-STAMP the ledger, so an agent can edit the same file
    repeatedly without being told its own edit made the file stale.
  * Bounded: per-session entry cap + session cap, both LRU-evicted, so a long
    run cannot grow memory without limit.
  * Fail-open: any internal error yields "allowed". This gate must never be the
    reason a legitimate edit fails.
"""
from __future__ import annotations

import contextvars
import hashlib
import os
from collections import OrderedDict
from typing import Optional

# Bound per tool call by src.tool_execution.execute_tool_block.
_active_session: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "agent_active_session", default=None,
)

_MAX_SESSIONS = 32
_MAX_FILES_PER_SESSION = 512

# session_key -> OrderedDict[realpath -> (mtime_ns, size, sha256)]
_LEDGER: "OrderedDict[str, OrderedDict[str, tuple]]" = OrderedDict()


def set_active_session(session_id: Optional[str]):
    """Bind the session for this tool call. Returns a token for reset()."""
    return _active_session.set(session_id or None)


def reset_active_session(token) -> None:
    try:
        _active_session.reset(token)
    except (ValueError, LookupError):
        pass


def current_session() -> Optional[str]:
    """The session bound for this tool call, if any (shared with checkpoints)."""
    return _active_session.get()


def _session_key() -> str:
    # A missing session id (e.g. cowork) still gets a stable bucket, so the
    # protection applies there too rather than silently disabling itself.
    return _active_session.get() or "__default__"


def _enabled() -> bool:
    try:
        from src.settings import get_setting
        return bool(get_setting("agent_read_before_edit", True))
    except Exception:
        return True


def _sig(path: str) -> Optional[tuple]:
    """(mtime_ns, size, sha256) for an existing file, or None if unreadable."""
    try:
        st = os.stat(path)
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        return (st.st_mtime_ns, st.st_size, digest)
    except OSError:
        return None


def _bucket(create: bool = False) -> Optional[OrderedDict]:
    key = _session_key()
    b = _LEDGER.get(key)
    if b is None:
        if not create:
            return None
        b = OrderedDict()
        _LEDGER[key] = b
        while len(_LEDGER) > _MAX_SESSIONS:
            _LEDGER.popitem(last=False)
    _LEDGER.move_to_end(key)
    return b


def record_read(path: str, content: Optional[str] = None) -> None:
    """Stamp *path* as read (or freshly written) in this session's ledger.

    `content` is accepted for symmetry with writers but the signature is always
    re-derived from disk, so the stamp reflects the bytes that are actually
    there — including any newline/encoding normalization the write applied.
    """
    if not path:
        return
    try:
        sig = _sig(path)
        if sig is None:
            return
        b = _bucket(create=True)
        if b is None:
            return
        real = os.path.realpath(path)
        b[real] = sig
        b.move_to_end(real)
        while len(b) > _MAX_FILES_PER_SESSION:
            b.popitem(last=False)
    except Exception:
        return


def forget(path: str) -> None:
    """Drop *path* from the ledger (after delete/move)."""
    try:
        b = _bucket()
        if b is None:
            return
        b.pop(os.path.realpath(path), None)
    except Exception:
        return


def check_editable(path: str, *, tool: str = "edit_file") -> Optional[str]:
    """Return an error string if *path* must not be modified yet, else None.

    Allowed without a prior read:
      * a path that does not exist yet (creating a new file), and
      * anything, when the gate is disabled via `agent_read_before_edit`.
    """
    if not path or not _enabled():
        return None
    try:
        if not os.path.exists(path):
            return None          # new file — nothing to clobber
        real = os.path.realpath(path)
        b = _bucket()
        seen = b.get(real) if b is not None else None
        if seen is None:
            return (
                f"{tool}: refusing to modify '{path}' because it has not been read "
                f"in this session. Call read_file on it first, then retry — this "
                f"prevents overwriting content you have not seen."
            )
        current = _sig(real)
        if current is None:
            return None          # unreadable now; the tool's own error will surface
        if current[0] == seen[0] and current[1] == seen[1]:
            return None          # mtime + size match — unchanged
        if current[2] == seen[2]:
            record_read(real)    # touched but identical bytes — re-stamp, allow
            return None
        return (
            f"{tool}: '{path}' changed on disk after you read it. Re-read the file "
            f"and re-apply your change to the current content — writing now would "
            f"discard the newer version."
        )
    except Exception:
        return None              # fail-open: never block a legitimate edit
