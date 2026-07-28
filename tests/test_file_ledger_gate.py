"""read-before-edit + stale-write gate (src/file_ledger.py).

Industry-standard coding agents refuse to modify a file they have not read this
session, and refuse to overwrite one that changed on disk since the read. Both
failures are silent and destructive, so they are enforced in the tool layer.
"""
import json
import os

import pytest

from src import file_ledger
from src.agent_tools.filesystem_tools import (
    EditFileTool, MultiEditTool, ReadFileTool, WriteFileTool,
)


@pytest.fixture
def target(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("a = 1\nb = 2\nc = 3\n")
    tok = file_ledger.set_active_session("test-session")
    yield str(p)
    file_ledger.reset_active_session(tok)


def _edit(path, old, new):
    return json.dumps({"path": path, "old_string": old, "new_string": new})


@pytest.mark.asyncio
async def test_edit_blocked_before_read(target):
    r = await EditFileTool().execute(_edit(target, "a = 1", "a = 9"), {})
    assert "has not been read" in r.get("error", "")


@pytest.mark.asyncio
async def test_write_file_cannot_clobber_unread_file(target):
    r = await WriteFileTool().execute(target + "\nCLOBBERED", {})
    assert "has not been read" in r.get("error", "")
    assert "CLOBBERED" not in open(target).read()


@pytest.mark.asyncio
async def test_new_file_creation_still_allowed(tmp_path):
    tok = file_ledger.set_active_session("test-session")
    try:
        q = str(tmp_path / "brand_new.py")
        r = await WriteFileTool().execute(q + "\nprint('hi')", {})
        assert r.get("exit_code") == 0
    finally:
        file_ledger.reset_active_session(tok)


@pytest.mark.asyncio
async def test_edit_allowed_after_read_and_repeatable(target):
    await ReadFileTool().execute(target, {})
    r = await EditFileTool().execute(_edit(target, "a = 1", "a = 9"), {})
    assert r.get("exit_code") == 0
    # A second edit in the same turn must not trip the staleness check on our
    # own write — the ledger is re-stamped after each successful write.
    r = await EditFileTool().execute(_edit(target, "b = 2", "b = 8"), {})
    assert r.get("exit_code") == 0


@pytest.mark.asyncio
async def test_external_change_blocks_write(target):
    await ReadFileTool().execute(target, {})
    os.utime(target, None)
    with open(target, "a") as f:
        f.write("d = 4\n")
    r = await EditFileTool().execute(_edit(target, "a = 1", "a = 0"), {})
    assert "changed on disk" in r.get("error", "")


@pytest.mark.asyncio
async def test_read_file_returns_line_numbers(target):
    r = await ReadFileTool().execute(target, {})
    assert r["output"].split("\n")[0] == "     1\ta = 1"


@pytest.mark.asyncio
async def test_line_numbered_old_string_is_auto_repaired(target):
    """A model that copies read_file's numbered output must still land its edit."""
    await ReadFileTool().execute(target, {})
    r = await EditFileTool().execute(_edit(target, "     3\tc = 3", "     3\tc = 7"), {})
    assert r.get("exit_code") == 0
    body = open(target).read()
    assert "c = 7" in body and "\t" not in body


@pytest.mark.asyncio
async def test_multi_edit_gated_then_allowed(target):
    payload = json.dumps({"path": target, "edits": [
        {"old_string": "a = 1", "new_string": "a = 9"},
        {"old_string": "b = 2", "new_string": "b = 8"},
    ]})
    r = await MultiEditTool().execute(payload, {})
    assert "has not been read" in r.get("error", "")
    await ReadFileTool().execute(target, {})
    r = await MultiEditTool().execute(payload, {})
    assert r.get("exit_code") == 0


@pytest.mark.asyncio
async def test_gate_is_session_scoped(target):
    await ReadFileTool().execute(target, {})
    tok = file_ledger.set_active_session("a-different-session")
    try:
        r = await EditFileTool().execute(_edit(target, "a = 1", "a = 9"), {})
        assert "has not been read" in r.get("error", "")
    finally:
        file_ledger.reset_active_session(tok)
