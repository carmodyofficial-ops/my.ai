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


def make_approval_cb(owner: str) -> Callable[[dict], object]:
    """Callback the agent loop calls SYNCHRONOUSLY to register a pending
    decision, returning an awaitable that resolves to the user's answer.

    Registering synchronously — before the loop emits `approval_required` —
    closes the race where a fast client resolves before the future exists.
    """
    def _cb(meta: dict):
        approval_id = str(meta.get("id") or "")
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        _PENDING[approval_id] = {"future": fut, "owner": owner}

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


def resolve(approval_id: str, approved: bool, owner: str) -> bool:
    """Resolve a pending approval.

    Returns False when unknown/expired, or owned by someone else — an approval
    may only be answered by the owner of the stream that raised it.
    """
    entry = _PENDING.get(approval_id)
    if not entry or entry.get("owner") != owner:
        return False
    fut = entry.get("future")
    if fut is not None and not fut.done():
        fut.set_result(bool(approved))
    return True


def pending_count() -> int:
    return len(_PENDING)
