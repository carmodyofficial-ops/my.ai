"""Owner-scoped productivity + history reads/writes for the wearables gateway.

The glasses companion shows recent notes, tasks, and calendar events (with a
quick-add), plus chat and Look-and-Ask history. Everything here is scoped to a
single `owner` username string — the value returned by
`require_wearables(request)` — so a device only ever sees or creates its own
owner's data, consistent with the gateway's confinement.

Deliberately compact: previews only (a few fields), reusing the same DB models
the web routes use so there is one source of truth.
"""

from __future__ import annotations

import json
import uuid

_MAX_TITLE = 200
_MAX_BODY = 4000
_MAX_DATE = 32  # room for any ISO-8601 date/datetime; keeps the field bounded


def _clip(s, n):
    s = (s or "").strip()
    return s[:n]


def _clip_date(s):
    """Bound a client-supplied date string; None/blank stays None."""
    s = (s or "").strip()
    return s[:_MAX_DATE] or None


def _snippet(text, n=120):
    t = (text or "").replace("\n", " ").strip()
    return t[: n - 1] + "…" if len(t) > n else t


# ── Notes ────────────────────────────────────────────────────────────────

def list_notes(owner: str, limit: int = 8) -> list[dict]:
    from core.database import get_db_session, Note
    with get_db_session() as db:
        # Hide archived notes (archived == the web app's Archive flag; a note the
        # user archived on the web must not resurface here). Notes are reference
        # text — no glasses "completion" concept, so no `done` field.
        rows = (db.query(Note)
                .filter(Note.owner == owner, Note.archived == False,  # noqa: E712
                        Note.note_type != "checklist")
                .order_by(Note.pinned.desc(), Note.updated_at.desc())
                .limit(limit).all())
        return [{
            "id": n.id,
            "title": n.title or "",
            "snippet": _snippet(n.content),
            "pinned": bool(n.pinned),
            "updated_at": str(getattr(n, "updated_at", "") or ""),
        } for n in rows]


def create_note(owner: str, title: str, content: str = "",
                date_iso: str | None = None) -> dict:
    from core.database import get_db_session, Note
    title, content = _clip(title, _MAX_TITLE), _clip(content, _MAX_BODY)
    if not title and not content:
        raise ValueError("empty note")
    date_iso = _clip_date(date_iso)
    nid = str(uuid.uuid4())
    with get_db_session() as db:
        db.add(Note(id=nid, owner=owner, title=title, content=content,
                    note_type="note", source="user", due_date=date_iso))
    return {"id": nid, "title": title, "snippet": _snippet(content),
            "due_date": date_iso}


# ── Tasks (checklist notes / to-dos) ───────────────────────────────────────

def list_tasks(owner: str, limit: int = 8) -> list[dict]:
    from core.database import get_db_session, Note
    with get_db_session() as db:
        # Hide web-archived checklists. Completion is per-item `done` (same field
        # the web app uses) — a task is "completed" (greyed) when ALL items are
        # done; completed tasks stay in the list (not archived) and can be toggled
        # back. This never touches Note.archived, so glasses + web agree.
        rows = (db.query(Note)
                .filter(Note.owner == owner, Note.archived == False,  # noqa: E712
                        Note.note_type == "checklist")
                .order_by(Note.pinned.desc(), Note.updated_at.desc())
                .limit(limit).all())
        out = []
        for n in rows:
            items = []
            if n.items:
                try:
                    items = json.loads(n.items) or []
                except (json.JSONDecodeError, TypeError):
                    items = []
            done = sum(1 for it in items if isinstance(it, dict) and it.get("done"))
            out.append({
                "id": n.id,
                "title": n.title or (items[0].get("text") if items else "") or "",
                "due_date": n.due_date or None,
                "completed": len(items) > 0 and done == len(items),  # greyed + toggle
                "done": done,                    # per-item done count (sub-label)
                "total": len(items),
            })
        return out


def create_task(owner: str, text: str, due_date: str | None = None) -> dict:
    from core.database import get_db_session, Note
    text = _clip(text, _MAX_TITLE)
    if not text:
        raise ValueError("empty task")
    due_date = _clip_date(due_date)
    nid = str(uuid.uuid4())
    items = json.dumps([{"text": text, "done": False}])
    with get_db_session() as db:
        db.add(Note(id=nid, owner=owner, title=text, items=items,
                    note_type="checklist", source="user",
                    due_date=due_date))
    return {"id": nid, "title": text, "due_date": due_date, "done": 0, "total": 1}


def complete_item(owner: str, note_id: str) -> bool | None:
    """Toggle a SINGLE-item checklist task's `done` flag (owner-scoped). Uses the
    same per-item `done` the web app uses; NEVER touches Note.archived (that is the
    web's Archive/hide flag). Returns the new completed state, or None if no such
    item for this owner.

    Deliberately a no-op (returns current state, no write) for:
      - plain notes (no completion concept), and
      - MULTI-item checklists (AI-created): a whole-note mark-all/unmark-all would
        clobber and then destroy individual per-item state, which the glasses UI
        can't edit. Those stay read-only on glasses; manage their items on the web.
    Also refuses to rewrite malformed/empty `items` (would discard the stored bytes).
    """
    from core.database import get_db_session, Note
    with get_db_session() as db:
        row = (db.query(Note)
               .filter(Note.owner == owner, Note.id == note_id).first())
        if row is None:
            return None
        if row.note_type != "checklist" or not row.items:
            return False
        try:
            items = json.loads(row.items)
        except (json.JSONDecodeError, TypeError):
            return False   # malformed — don't overwrite the stored bytes
        if not isinstance(items, list) or not items:
            return False
        done_now = all(isinstance(it, dict) and it.get("done") for it in items)
        if len(items) > 1 or not isinstance(items[0], dict):
            return done_now   # multi-item / non-dict item → read-only, report only
        new_done = not bool(items[0].get("done"))
        items[0]["done"] = new_done
        row.items = json.dumps(items)
        return new_done


# ── Chat history ───────────────────────────────────────────────────────────

def list_chats(owner: str, limit: int = 20) -> list[dict]:
    """Recent chat conversations for this owner, newest first."""
    try:
        from core.session_manager import session_manager
    except Exception:
        return []
    # Pass owner as-is (never coalesce "" → None): an empty owner must filter to
    # empty-owner sessions, not broaden to every user's, matching list_notes.
    sessions = session_manager.get_sessions_for_user(owner)
    items = []
    for sid, s in sessions.items():
        items.append({
            "id": sid,
            "name": getattr(s, "name", None) or "Conversation",
            "updated_at": str(getattr(s, "last_message_at", None)
                              or getattr(s, "updated_at", "") or ""),
            "messages": len(getattr(s, "history", []) or []),
        })
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return items[:limit]


# ── Look-and-Ask (vision) history ──────────────────────────────────────────

def log_vision(owner: str, question: str, answer: str) -> None:
    """Persist one Look-and-Ask exchange (no image is stored — text only)."""
    from core.database import get_db_session, WearableVisionLog
    with get_db_session() as db:
        db.add(WearableVisionLog(
            id=str(uuid.uuid4()), owner=owner,
            question=_clip(question, _MAX_TITLE), answer=_clip(answer, _MAX_BODY)))


def list_vision(owner: str, limit: int = 20) -> list[dict]:
    from core.database import get_db_session, WearableVisionLog
    with get_db_session() as db:
        rows = (db.query(WearableVisionLog)
                .filter(WearableVisionLog.owner == owner)
                .order_by(WearableVisionLog.created_at.desc())
                .limit(limit).all())
        return [{
            "id": r.id,
            "question": r.question or "",
            "answer": _snippet(r.answer, 160),
            "created_at": str(getattr(r, "created_at", "") or ""),
        } for r in rows]
