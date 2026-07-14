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


def test_delete_item_removes_owned_row(memdb):
    nid = _add(memdb, owner="alice", note_type="todo",
               items=json.dumps([{"text": "x", "done": False}]))
    assert prod.delete_item("alice", nid) is True
    s = memdb()
    assert s.query(db.Note).filter(db.Note.id == nid).first() is None   # gone
    s.close()
    assert prod.delete_item("alice", nid) is False       # already gone → no-op


def test_delete_item_is_owner_scoped(memdb):
    nid = _add(memdb, owner="alice", note_type="note", content="mine")
    assert prod.delete_item("bob", nid) is False         # not bob's — refused
    s = memdb()
    assert s.query(db.Note).filter(db.Note.id == nid).first() is not None  # untouched
    s.close()
    assert prod.delete_item("alice", "missing") is False # missing → no-op


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


def test_create_task_is_a_web_todo_and_toggles(memdb):
    # A glasses task is created as a web-checkable 'todo' (so it renders + syncs on
    # the web), shows in Tasks (not Notes), and toggles.
    r = prod.create_task("alice", "buy milk")
    s = memdb()
    assert s.query(db.Note).filter(db.Note.id == r["id"]).first().note_type == "todo"
    s.close()
    assert [t["id"] for t in prod.list_tasks("alice")] == [r["id"]]
    assert prod.list_notes("alice") == []
    assert prod.complete_item("alice", r["id"]) is True
    assert prod.complete_item("alice", r["id"]) is False


def test_todo_checklist_are_tasks_goal_and_notes_are_reference(memdb):
    _add(memdb, owner="alice", note_type="todo",
         items=json.dumps([{"text": "a", "done": False}]))
    _add(memdb, owner="alice", note_type="checklist",
         items=json.dumps([{"text": "b", "done": False}]))
    # A 'goal' is a big multi-step objective — reference, NOT a quick task; it must
    # NOT clog the Tasks card. It falls into the Notes card instead.
    _add(memdb, owner="alice", note_type="goal", content="run a marathon",
         items=json.dumps([{"text": "c", "done": False}]))
    _add(memdb, owner="alice", note_type="note", content="ref")
    _add(memdb, owner="alice", note_type=None, content="legacy")   # null → a note
    assert len(prod.list_tasks("alice")) == 2
    assert sorted(n["snippet"] for n in prod.list_notes("alice")) == [
        "legacy", "ref", "run a marathon"]


def test_create_task_leaves_title_empty_to_avoid_double_render(memdb):
    # The web renders a checkable to-do from items[]; a non-empty title would render
    # a SECOND time as a header row. We store title="" and let the glasses label fall
    # back to the item text.
    r = prod.create_task("alice", "buy milk")
    s = memdb()
    assert s.query(db.Note).filter(db.Note.id == r["id"]).first().title == ""
    s.close()
    assert prod.list_tasks("alice")[0]["title"] == "buy milk"   # item-text fallback


def test_active_tasks_sort_before_completed_within_the_cap(memdb):
    # Completed (all-items-done) tasks must sink below active ones so a pile of
    # finished tasks can't bury active work in the capped card.
    for i in range(8):
        _add(memdb, owner="alice", note_type="todo",
             items=json.dumps([{"text": f"done{i}", "done": True}]))
    active = _add(memdb, owner="alice", note_type="todo",
                  items=json.dumps([{"text": "ACTIVE", "done": False}]))
    tasks = prod.list_tasks("alice", limit=8)
    assert len(tasks) == 8
    assert tasks[0]["id"] == active and tasks[0]["completed"] is False
