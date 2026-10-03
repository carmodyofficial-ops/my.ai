"""Shared per-tool-call approval registry.

The agent loop can pause before a mutating tool and await a human decision
(`approval_cb` in `stream_agent_loop`). That gate was well built but had exactly
one client — the `myai` terminal script behind an env var — so browser users, the
primary surface, had no approval at all: edits simply landed and the diff showed
up afterwards.

This module holds the registry so the cowork route and the chat route share one
implementation instead of drifting copies, and defines the approval TIERS.

Tier design note: `write_file` / `edit_file` / `multi_edit` are deliberately NOT
in the "destructive" tier. Every one of them now snapshots the file first and is
revertible from the UI (see src/file_checkpoints.py), so prompting for them buys
little and costs approval fatigue — which is the failure mode that makes people
switch approval off entirely. The tier covers what is genuinely hard to take
back: code execution and filesystem removal/relocation.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)

APPROVAL_TTL = 300  # seconds to wait for a decision before auto-denying

# approval_id -> {"future": Future, "owner": str}
_PENDING: Dict[str, dict] = {}

# Hard to undo: runs code, or removes/relocates files.
DESTRUCTIVE_TOOLS: Set[str] = {
    "bash", "python", "code_sandbox",
    "delete_file", "move_file",
    "apply_patch", "git",
    "http_request",
}

VALID_MODES = ("off", "destructive", "all")

# "Allow for this chat": (owner, session_id) -> tool names auto-approved for the
# rest of that chat. In memory on purpose — a restart (or a new chat) asks again.
_SESSION_ALLOW: Dict[tuple, Set[str]] = {}


def stricter_mode(operator_mode: str, client_mode: str) -> str:
    """The stricter of the operator's setting and a per-chat request.

    A client (the "Ask first" switch) may only ADD approvals; it can never
    loosen the operator's setting.
    """
    order = {m: i for i, m in enumerate(VALID_MODES)}
    a = (operator_mode or "off").strip().lower()
    b = (client_mode or "off").strip().lower()
    a = a if a in order else "off"
    b = b if b in order else "off"
    return a if order[a] >= order[b] else b


def session_allowed(owner: str, session_id: Optional[str]) -> Set[str]:
    return set(_SESSION_ALLOW.get((owner, session_id or ""), ()))


def clear_session_allow(owner: str, session_id: Optional[str]) -> None:
    _SESSION_ALLOW.pop((owner, session_id or ""), None)


def tools_for_mode(mode: str) -> Optional[Set[str]]:
    """Tool set requiring approval for *mode*, or None when approval is off.

    "all" returns None meaning "use the agent loop's full default set".
    """
    m = (mode or "off").strip().lower()
    if m == "destructive":
        return set(DESTRUCTIVE_TOOLS)
    if m == "all":
        return None
    return None


def approval_enabled(mode: str) -> bool:
    return (mode or "off").strip().lower() in ("destructive", "all")


def make_approval_cb(owner: str, session_id: Optional[str] = None) -> Callable[[dict], object]:
    """Callback the agent loop calls SYNCHRONOUSLY to register a pending
    decision, returning an awaitable that resolves to the user's answer.

    Registering synchronously — before the loop emits `approval_required` —
    closes the race where a fast client resolves before the future exists.

    A tool the user chose "Allow for this chat" for returns an already-resolved
    future (``fut.done()`` is True), which the loop takes as "don't prompt".
    """
    def _cb(meta: dict):
        approval_id = str(meta.get("id") or "")
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        tool = str(meta.get("tool") or "")
        if session_id and tool and tool in _SESSION_ALLOW.get((owner, session_id), ()):
            fut.set_result(True)
            return fut
        _PENDING[approval_id] = {"future": fut, "owner": owner,
                                 "session_id": session_id, "tool": tool}

        async def _wait() -> bool:
            try:
                return bool(await asyncio.wait_for(fut, timeout=APPROVAL_TTL))
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # No decision (tab closed, user walked away) → deny. Fail-closed
                # is the only safe default for "may I run this on your machine".
                return False
            finally:
                _PENDING.pop(approval_id, None)

        return _wait()
    return _cb


def resolve(approval_id: str, approved: bool, owner: str, remember: bool = False) -> bool:
    """Resolve a pending approval.

    Returns False when unknown/expired, or owned by someone else — an approval
    may only be answered by the owner of the stream that raised it.
    ``remember`` (with approved) auto-approves this tool for the rest of the chat.
    """
    entry = _PENDING.get(approval_id)
    if not entry or entry.get("owner") != owner:
        return False
    if approved and remember and entry.get("session_id") and entry.get("tool"):
        _SESSION_ALLOW.setdefault((owner, entry["session_id"]), set()).add(entry["tool"])
    fut = entry.get("future")
    if fut is not None and not fut.done():
        fut.set_result(bool(approved))
    return True


def pending_count() -> int:
    return len(_PENDING)
