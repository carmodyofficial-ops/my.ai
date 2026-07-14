"""Direct unit tests for the wearables productivity layer.

The route tests (test_wearables_routes) monkeypatch these functions, so the REAL
DB logic — the complete_item toggle semantics and the list archived-filter — was
uncovered. These exercise it against an in-memory SQLite DB. In particular they
pin the data-integrity contracts:
  - complete_item NEVER writes Note.archived (the web app's Archive flag), and
  - a MULTI-item checklist is read-only (no mark-all clobber of per-item state).
"""

import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import core.database as db  # noqa: E402
from services.wearables_gateway import productivity as prod  # noqa: E402


@pytest.fixture
def memdb(monkeypatch):
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    return TestSession


def _add(TestSession, **kw):
    nid = kw.pop("id", None) or str(uuid.uuid4())
    s = TestSession()
    s.add(db.Note(id=nid, **kw))
    s.commit()
    s.close()
    return nid


def _items(TestSession, nid):
    s = TestSession()
    raw = s.query(db.Note).filter(db.Note.id == nid).first().items
    s.close()
    return raw


def test_single_item_toggles(memdb):
    nid = _add(memdb, owner="alice", note_type="checklist",
               items=json.dumps([{"text": "x", "done": False}]))
    assert prod.complete_item("alice", nid) is True
    assert prod.complete_item("alice", nid) is False


def test_multi_item_is_readonly_no_clobber(memdb):
    items = [{"text": "a", "done": True},
             {"text": "b", "done": False},
             {"text": "c", "done": False}]
    nid = _add(memdb, owner="alice", note_type="checklist", items=json.dumps(items))
    # No-op: reports current all-done (False) WITHOUT touching per-item state.
    assert prod.complete_item("alice", nid) is False
    assert json.loads(_items(memdb, nid)) == items   # partial state preserved


def test_malformed_items_not_overwritten(memdb):
    nid = _add(memdb, owner="alice", note_type="checklist", items="NOTJSON")
    assert prod.complete_item("alice", nid) is False
    assert _items(memdb, nid) == "NOTJSON"   # stored bytes untouched


def test_note_and_empty_checklist_are_noops(memdb):
    note = _add(memdb, owner="alice", note_type="note", content="hi")
    empty = _add(memdb, owner="alice", note_type="checklist", items=None)
    assert prod.complete_item("alice", note) is False
    assert prod.complete_item("alice", empty) is False


def test_never_writes_archived(memdb):
    nid = _add(memdb, owner="alice", note_type="checklist",
               items=json.dumps([{"text": "x", "done": False}]))
    prod.complete_item("alice", nid)
    s = memdb()
    assert s.query(db.Note).filter(db.Note.id == nid).first().archived is False
    s.close()


def test_cross_owner_and_missing_return_none(memdb):
    nid = _add(memdb, owner="alice", note_type="checklist",
               items=json.dumps([{"text": "x", "done": False}]))
    assert prod.complete_item("bob", nid) is None        # not this owner
    assert prod.complete_item("alice", "nope") is None   # missing


def test_lists_hide_archived(memdb):
    _add(memdb, owner="alice", note_type="note", content="active")
    _add(memdb, owner="alice", note_type="note", content="hidden", archived=True)
    _add(memdb, owner="alice", note_type="checklist", archived=True,
         items=json.dumps([{"text": "t", "done": False}]))
    assert [n["snippet"] for n in prod.list_notes("alice")] == ["active"]
    assert prod.list_tasks("alice") == []


def test_list_tasks_completed_flag(memdb):
    _add(memdb, owner="alice", note_type="checklist",
         items=json.dumps([{"text": "x", "done": True}]))
    tasks = prod.list_tasks("alice")
    assert len(tasks) == 1 and tasks[0]["completed"] is True
