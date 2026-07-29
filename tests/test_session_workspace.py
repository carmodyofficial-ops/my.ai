"""Per-session workspace binding.

The workspace used to live only in browser localStorage and was GLOBAL, so
opening a different chat silently kept the previous project. With two repos open
that is a correctness risk, not just an annoyance: the agent can edit the wrong
one. Sessions now remember their project.

The binding is a remembered PREFERENCE, never an authorization decision — every
request re-vets the path, so a stale or tampered row cannot widen file access.
"""
import sqlite3

import pytest

import core.database as D
from core.database import Session as DbSession, SessionLocal
from core.session_manager import SessionManager


def test_sessions_table_has_workspace_column():
    assert "workspace" in [c.name for c in DbSession.__table__.columns]


def test_migration_added_the_column_to_the_live_db():
    """The ALTER must have run — a model-only column would break on write."""
    path = D.DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(path)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)")]
    finally:
        conn.close()
    assert "workspace" in cols


def test_migration_is_idempotent():
    """Re-running must not raise — startup calls it on every boot."""
    D._migrate_add_session_workspace_column()
    D._migrate_add_session_workspace_column()


@pytest.fixture
def a_session():
    sm = SessionManager()
    ids = list(sm.sessions.keys())
    if not ids:
        pytest.skip("no sessions in this database to bind")
    sid = ids[0]
    db = SessionLocal()
    try:
        original = db.query(DbSession).filter(DbSession.id == sid).first().workspace
    finally:
        db.close()
    yield sm, sid
    sm.update_session_workspace(sid, original)


def _stored(sid):
    db = SessionLocal()
    try:
        return db.query(DbSession).filter(DbSession.id == sid).first().workspace
    finally:
        db.close()


def test_workspace_persists_and_can_be_unbound(a_session):
    sm, sid = a_session
    sm.update_session_workspace(sid, "/app")
    assert _stored(sid) == "/app"
    # Survives a fresh manager — proves it is on the row, not just in memory.
    SessionManager()
    assert _stored(sid) == "/app"
    sm.update_session_workspace(sid, None)
    assert _stored(sid) is None


def test_empty_string_unbinds_rather_than_storing_blank(a_session):
    sm, sid = a_session
    sm.update_session_workspace(sid, "")
    assert _stored(sid) is None


def test_unknown_session_id_is_a_no_op(a_session):
    """Must not raise or create a row for a session that isn't loaded."""
    sm, _ = a_session
    sm.update_session_workspace("no-such-session-id", "/app")


def test_remembered_workspace_is_re_vetted_not_trusted():
    """A saved path still goes through vet_workspace on every request.

    Guards the property that makes this safe to persist: vet_workspace rejects
    non-directories, sensitive roots and filesystem roots, so a tampered row
    cannot hand the agent a wider scope than a client-supplied path could.
    """
    import inspect

    from routes import chat_routes

    src = inspect.getsource(chat_routes.setup_chat_routes)
    # The restore path must call the same resolver used for client input.
    assert "_resolve_request_workspace(request, sess.workspace)" in src

    from src.tool_execution import vet_workspace
    assert vet_workspace("/etc/passwd") is None       # not a directory
    assert vet_workspace("/") is None                 # filesystem root
    assert vet_workspace("/nonexistent-dir-xyz") is None
