"""Pre-edit checkpoints / undo (src/file_checkpoints.py).

The agent's file tools snapshot a file before modifying it so a change can be
reverted — per file, or a whole turn. Previously the live edit path had no undo
at all: the original content survived only inside a truncated display diff.
"""
import json
import os

import pytest

from src import file_checkpoints, file_ledger
from src.agent_tools.filesystem_tools import (
    DeleteFileTool, EditFileTool, ReadFileTool, WriteFileTool,
)


@pytest.fixture
def session(tmp_path, monkeypatch):
    # Keep checkpoints out of the real data dir.
    monkeypatch.setattr("src.constants.DATA_DIR", str(tmp_path / "data"), raising=False)
    tok = file_ledger.set_active_session("cp-test")
    file_checkpoints.begin_group("cp-test")
    yield "cp-test"
    file_ledger.reset_active_session(tok)


def _edit(path, old, new):
    return json.dumps({"path": path, "old_string": old, "new_string": new})


@pytest.mark.asyncio
async def test_edit_records_checkpoint_and_undo_restores(session, tmp_path):
    p = tmp_path / "x.py"
    p.write_text("ORIGINAL\n")
    await ReadFileTool().execute(str(p), {})
    r = await EditFileTool().execute(_edit(str(p), "ORIGINAL", "CHANGED"), {})
    assert r["exit_code"] == 0 and r.get("checkpoint_id")
    assert p.read_text().strip() == "CHANGED"

    res = file_checkpoints.restore(r["checkpoint_id"], session_id=session)
    assert res["ok"]
    assert p.read_text().strip() == "ORIGINAL"


@pytest.mark.asyncio
async def test_undo_of_a_created_file_deletes_it(session, tmp_path):
    q = tmp_path / "new.py"
    r = await WriteFileTool().execute(f"{q}\nbrand new\n", {})
    assert r["exit_code"] == 0 and q.exists()
    res = file_checkpoints.restore(r["checkpoint_id"], session_id=session)
    assert res["ok"] and res["action"] == "deleted"
    assert not q.exists()


@pytest.mark.asyncio
async def test_undo_of_a_delete_restores_content(session, tmp_path):
    p = tmp_path / "gone.py"
    p.write_text("KEEP ME\n")
    await ReadFileTool().execute(str(p), {})
    r = await DeleteFileTool().execute(json.dumps({"path": str(p)}), {})
    assert r["exit_code"] == 0 and not p.exists()
    res = file_checkpoints.restore(r["checkpoint_id"], session_id=session)
    assert res["ok"] and p.read_text().strip() == "KEEP ME"


@pytest.mark.asyncio
async def test_group_undo_reverts_whole_turn_including_double_edit(session, tmp_path):
    """A file edited twice in one turn must return to its PRE-TURN state.

    Guards the newest-first replay order: applying the oldest snapshot last is
    what makes the final content the original rather than the intermediate.
    """
    group = file_checkpoints.begin_group(session)
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("A0\n")
    b.write_text("B0\n")
    await ReadFileTool().execute(str(a), {})
    await ReadFileTool().execute(str(b), {})
    await EditFileTool().execute(_edit(str(a), "A0", "A1"), {})
    await EditFileTool().execute(_edit(str(b), "B0", "B1"), {})
    await EditFileTool().execute(_edit(str(a), "A1", "A2"), {})
    assert a.read_text().strip() == "A2"

    res = file_checkpoints.restore_group(group, session_id=session)
    assert res["ok"]
    assert a.read_text().strip() == "A0"
    assert b.read_text().strip() == "B0"


@pytest.mark.asyncio
async def test_restore_clears_read_ledger(session, tmp_path):
    """After an undo the agent must re-read before it may edit again."""
    p = tmp_path / "x.py"
    p.write_text("V0\n")
    await ReadFileTool().execute(str(p), {})
    r = await EditFileTool().execute(_edit(str(p), "V0", "V1"), {})
    file_checkpoints.restore(r["checkpoint_id"], session_id=session)
    r2 = await EditFileTool().execute(_edit(str(p), "V0", "V9"), {})
    assert "has not been read" in r2.get("error", "")


@pytest.mark.asyncio
async def test_listing_is_metadata_only(session, tmp_path):
    p = tmp_path / "x.py"
    p.write_text("secret content\n")
    await ReadFileTool().execute(str(p), {})
    await EditFileTool().execute(_edit(str(p), "secret content", "other"), {})
    items = file_checkpoints.list_checkpoints(session, limit=10)
    assert items
    assert all("content" not in i for i in items)
    assert file_checkpoints.latest_group(session) == items[0]["group"]
