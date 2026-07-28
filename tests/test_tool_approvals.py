"""Per-tool-call approval registry (src/tool_approvals.py).

The agent loop pauses before a mutating tool and blocks until a decision
arrives. Two properties are security-critical and tested here:
  * an approval may only be answered by the OWNER of the stream that raised it;
  * no decision (tab closed, user away) must DENY, never allow.
"""
import asyncio

import pytest

from src import tool_approvals


@pytest.mark.asyncio
async def test_allow_resolves_true_and_unregisters():
    cb = tool_approvals.make_approval_cb("alice")
    waiter = cb({"id": "a1", "tool": "bash", "command": "ls"})
    assert tool_approvals.resolve("a1", True, "alice") is True
    assert await waiter is True
    assert tool_approvals.pending_count() == 0


@pytest.mark.asyncio
async def test_deny_resolves_false():
    cb = tool_approvals.make_approval_cb("alice")
    waiter = cb({"id": "a2", "tool": "delete_file", "command": "x"})
    tool_approvals.resolve("a2", False, "alice")
    assert await waiter is False


@pytest.mark.asyncio
async def test_another_user_cannot_resolve_your_approval():
    cb = tool_approvals.make_approval_cb("alice")
    waiter = cb({"id": "a3", "tool": "bash", "command": "rm -rf /"})
    assert tool_approvals.resolve("a3", True, "bob") is False
    assert tool_approvals.resolve("a3", False, "alice") is True
    assert await waiter is False


def test_unknown_approval_id_is_refused():
    assert tool_approvals.resolve("does-not-exist", True, "alice") is False


@pytest.mark.asyncio
async def test_no_decision_fails_closed(monkeypatch):
    monkeypatch.setattr(tool_approvals, "APPROVAL_TTL", 0.05)
    cb = tool_approvals.make_approval_cb("alice")
    waiter = cb({"id": "a4", "tool": "bash", "command": "x"})
    assert await waiter is False           # timeout → deny
    assert tool_approvals.pending_count() == 0


def test_destructive_tier_excludes_undoable_edits():
    """Edits are snapshotted and revertible, so they are not worth a prompt.

    Gating them too is what produces approval fatigue — the failure mode that
    makes people turn approval off entirely. See src/file_checkpoints.py.
    """
    tier = tool_approvals.tools_for_mode("destructive")
    assert {"bash", "python", "delete_file", "move_file", "git"} <= tier
    assert "edit_file" not in tier
    assert "write_file" not in tier
    assert "multi_edit" not in tier


def test_mode_gating():
    assert tool_approvals.approval_enabled("destructive")
    assert tool_approvals.approval_enabled("all")
    assert not tool_approvals.approval_enabled("off")
    assert not tool_approvals.approval_enabled("")
    # "all" defers to the agent loop's own full default set.
    assert tool_approvals.tools_for_mode("all") is None
