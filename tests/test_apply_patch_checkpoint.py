"""apply_patch is checkpointed and reports its changed files.

Two gaps this closes:
  * it was the only mutating tool with no pre-change snapshot, so a multi-file
    patch could not be undone;
  * it returned neither `path` nor `paths`, so patched files were skipped by
    the post-edit syntax check that covers every other edit tool.
"""
import json
import os
import subprocess

import pytest

from src import file_checkpoints, file_ledger
from src.agent_tools.coding_tools import ApplyPatchTool
from src.tool_execution import _active_workspace


def _git(repo, *args, **kw):
    return subprocess.run(["git", "-C", repo, *args], check=True,
                          capture_output=True, text=True, **kw)


@pytest.fixture
def repo_with_patch(tmp_path, monkeypatch):
    monkeypatch.setattr("src.constants.DATA_DIR", str(tmp_path / "data"), raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    f = repo / "m.py"
    f.write_text("x = 1\n")
    _git(str(repo), "add", ".")
    _git(str(repo), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    f.write_text("x = 2\n")
    patch = _git(str(repo), "diff").stdout
    _git(str(repo), "checkout", "--", ".")
    assert f.read_text() == "x = 1\n"

    ws_token = _active_workspace.set(str(repo))
    sess_token = file_ledger.set_active_session("patch-test")
    group = file_checkpoints.begin_group("patch-test")
    yield {"repo": str(repo), "file": f, "patch": patch, "group": group}
    file_ledger.reset_active_session(sess_token)
    _active_workspace.reset(ws_token)


@pytest.mark.asyncio
async def test_apply_patch_reports_paths_and_is_undoable(repo_with_patch):
    ctx = repo_with_patch
    result = await ApplyPatchTool().execute(
        json.dumps({"patch": ctx["patch"]}), {})
    assert result.get("exit_code") == 0
    assert ctx["file"].read_text() == "x = 2\n"

    # Changed files are reported, so the post-edit syntax check can see them.
    assert result.get("paths")
    assert os.path.basename(result["paths"][0]) == "m.py"

    # And the pre-patch state was snapshotted, so the change is undoable.
    assert result.get("checkpoint_ids")
    res = file_checkpoints.restore_group(ctx["group"], session_id="patch-test")
    assert res["ok"]
    assert ctx["file"].read_text() == "x = 1\n"
