"""Transient, in-memory conversation sessions for wearable devices.

Privacy-by-default: nothing here touches the database or ChromaDB. A session
holds the short rolling context for follow-up questions and dies with the
process, on DELETE, or after IDLE_TTL_SECONDS. Durable transcript storage /
Odysseus memory proposals are a later, opt-in integration through the
documented /api/memory interfaces — never a silent side effect of talking to
your glasses.
"""

from __future__ import annotations

import asyncio
import re
import itertools
import threading
import time
import uuid
from dataclasses import dataclass, field

IDLE_TTL_SECONDS = 30 * 60
MAX_TURNS_KEPT = 12          # rolling context window (user+assistant messages)
MAX_SESSIONS_PER_OWNER = 20
# Hard ceiling for a session stuck busy=True. busy is set before the streaming
# response starts and cleared in the generator's finally; if that generator is
# closed before its first iteration (client vanished before the body streamed),
# the finally never runs and the session would otherwise be immortal — exempt
# from idle-prune AND from the owner cap forever. Past this age a busy session
# is reclaimed regardless.
BUSY_MAX_SECONDS = 10 * 60
# A claim whose stream never started iterating within this window is
# abandoned: the handler claimed the session but Starlette never ran the
# generator (client gone before the body streamed), so no finally will ever
# release it. A started stream is trusted up to BUSY_MAX_SECONDS.
BUSY_UNSTARTED_GRACE_SECONDS = 30

_BUSY_TOKENS = itertools.count(1)

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@dataclass
class WearableSession:
    id: str
    owner: str
    created_at: float = field(default_factory=time.monotonic)
    last_active: float = field(default_factory=time.monotonic)
    messages: list[dict] = field(default_factory=list)
    store_transcript: bool = True  # in-memory rolling context only
    cancel_event: asyncio.Event | None = None
    busy: bool = False
    busy_since: float = 0.0       # monotonic time of the current claim
    busy_token: int = 0           # identifies the claim that owns busy
    stream_started: bool = False  # the claim's generator began iterating

    # Busy is age-based, measured from the claim, NOT from last_active.
    # Keying staleness on last_active was the original bug: every rejected
    # request touch()ed the session, so a stuck one never aged out.
    def _busy_stale(self, now: float) -> bool:
        if not self.busy_since:  # busy set directly, not via claim()
            return now - self.created_at > BUSY_MAX_SECONDS
        age = now - self.busy_since
        if not self.stream_started and age > BUSY_UNSTARTED_GRACE_SECONDS:
            return True
        return age > BUSY_MAX_SECONDS

    def is_busy(self, now: float | None = None) -> bool:
        if not self.busy:
            return False
        return not self._busy_stale(time.monotonic() if now is None else now)

    def claim(self) -> int | None:
        """Take the one-in-flight slot. Returns a token, or None if a live
        stream holds it. A stale claim is overridden."""
        if self.is_busy():
            return None
        self.busy = True
        self.busy_since = time.monotonic()
        self.stream_started = False
        self.busy_token = next(_BUSY_TOKENS)
        self.cancel_event = None
        return self.busy_token

    def mark_started(self, token: int) -> None:
        if self.busy and self.busy_token == token:
            self.stream_started = True

    def release(self, token: int) -> None:
        """Idempotent. A release from a superseded (stale) claim is ignored so
        a late-finishing old stream can't clear a newer one's busy flag."""
        if self.busy_token != token:
            return
        self.busy = False
        self.stream_started = False
        self.cancel_event = None
        self.touch()

    def touch(self) -> None:
        self.last_active = time.monotonic()

    def append_turn(self, user_text: str, assistant_text: str) -> None:
        if not self.store_transcript:
            return
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})
        if len(self.messages) > MAX_TURNS_KEPT:
            del self.messages[: len(self.messages) - MAX_TURNS_KEPT]


class WearableSessionStore:
    """Owner-scoped session registry. All lookups require the caller's owner
    and never return another owner's session."""

    def __init__(self, idle_ttl: int = IDLE_TTL_SECONDS):
        self.idle_ttl = idle_ttl
        self._sessions: dict[str, WearableSession] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str | None, owner: str,
                      store_transcript: bool = True) -> WearableSession:
        sid = session_id if session_id and _SESSION_ID_RE.match(session_id) else None
        with self._lock:
            self._prune()
            if sid:
                existing = self._sessions.get(sid)
                if existing is not None and existing.owner == owner:
                    existing.touch()
                    return existing
            new_id = sid or uuid.uuid4().hex
            # A valid-looking id owned by someone else must not be joinable:
            # collide → mint a fresh id instead of sharing context.
            if new_id in self._sessions:
                new_id = uuid.uuid4().hex
            sess = WearableSession(id=new_id, owner=owner,
                                   store_transcript=store_transcript)
            self._sessions[new_id] = sess
            self._enforce_owner_cap(owner)
            return sess

    def get(self, session_id: str, owner: str) -> WearableSession | None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None or sess.owner != owner:
                return None
            return sess

    def delete(self, session_id: str, owner: str) -> bool:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None or sess.owner != owner:
                return False
            if sess.cancel_event is not None:
                sess.cancel_event.set()
            del self._sessions[session_id]
            return True

    def cancel(self, session_id: str, owner: str) -> bool:
        """Signal the active stream (if any) for this session to stop."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None or sess.owner != owner:
                return False
            if sess.cancel_event is not None:
                sess.cancel_event.set()
                return True
            return False

    def count(self) -> int:
        with self._lock:
            self._prune()
            return len(self._sessions)

    def _reclaimable(self, s: "WearableSession", now: float) -> bool:
        """A busy session is normally protected from pruning, but not forever —
        a stuck-busy session (generator closed before it could clear the flag)
        must not become immortal."""
        return not s.is_busy(now)

    def _prune(self) -> None:
        now = time.monotonic()
        stale = [sid for sid, s in self._sessions.items()
                 if self._reclaimable(s, now) and now - s.last_active > self.idle_ttl]
        for sid in stale:
            del self._sessions[sid]

    def _enforce_owner_cap(self, owner: str) -> None:
        now = time.monotonic()
        mine = [s for s in self._sessions.values() if s.owner == owner]
        if len(mine) <= MAX_SESSIONS_PER_OWNER:
            return
        mine.sort(key=lambda s: s.last_active)
        for s in mine[: len(mine) - MAX_SESSIONS_PER_OWNER]:
            if self._reclaimable(s, now):
                self._sessions.pop(s.id, None)
