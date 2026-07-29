"""apply_patch is checkpointed and reports its changed files.

Two gaps this closes:
  * it was the only mutating tool with no pre-change snapshot, so a multi-file
    patch could not be undone;
  * it returned neither `path` nor `paths`, so patched files were skipped by
    the post-edit syntax check that covers every other edit tool.

Isolation note: this test pins the tool's working directory by patching
`agent_cwd` rather than binding the workspace contextvar. Earlier versions did
the latter (directly, then via execute_tool_block) and both passed alone but
failed in a full-suite run with `git apply` resolving the wrong directory — the
ambient binding did not reach the tool. Nothing here now depends on ambient
per-turn state, so the result is the same however the suite is ordered.
"""
import json
import os
import subprocess

import pytest

from src import file_checkpoints
from src.agent_tools.coding_tools import ApplyPatchTool


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True,
                          capture_output=True, text=True)


@pytest.fixture
def repo_with_patch(tmp_path, monkeypatch):
    # Keep checkpoints out of the real data dir.
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
    assert patch.strip(), "fixture produced an empty patch"

    # ApplyPatchTool resolves its working directory through agent_cwd() at call
    # time, so patching it here is exact and order-independent.
    monkeypatch.setattr("src.tool_execution.agent_cwd", lambda: str(repo))
    return {"repo": str(repo), "file": f, "patch": patch}


@pytest.mark.asyncio
async def test_apply_patch_reports_paths_and_is_undoable(repo_with_patch):
    ctx = repo_with_patch
    result = await ApplyPatchTool().execute(json.dumps({"patch": ctx["patch"]}), {})

    assert result.get("exit_code") == 0, result
    assert ctx["file"].read_text() == "x = 2\n"

    # Changed files are reported, so the post-edit syntax check can see them.
    assert result.get("paths"), result
    assert os.path.basename(result["paths"][0]) == "m.py"

    # The pre-patch state was snapshotted, so the change is undoable. Restore by
    # checkpoint id rather than group: the group is another ambient binding, and
    # the ids come straight back from the call.
    ids = result.get("checkpoint_ids")
    assert ids, result
    for cid in ids:
        assert file_checkpoints.restore(cid)["ok"]
    assert ctx["file"].read_text() == "x = 1\n"
