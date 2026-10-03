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


# ── Per-chat "Ask first" + "Allow for this chat" ────────────────────────────

def test_client_can_only_make_approval_stricter():
    sm = tool_approvals.stricter_mode
    assert sm("off", "all") == "all"            # Ask first escalates
    assert sm("destructive", "all") == "all"
    assert sm("all", "off") == "all"            # a client can't loosen the operator
    assert sm("destructive", "") == "destructive"
    assert sm("off", "bogus") == "off"


@pytest.mark.asyncio
async def test_allow_for_this_chat_auto_approves_same_tool_only():
    tool_approvals.clear_session_allow("alice", "chat1")
    cb = tool_approvals.make_approval_cb("alice", "chat1")
    w = cb({"id": "s1", "tool": "bash", "command": "ls"})
    assert tool_approvals.resolve("s1", True, "alice", remember=True) is True
    assert await w is True
    # Same tool, same chat: pre-approved (a done future, so the loop won't prompt).
    w2 = cb({"id": "s2", "tool": "bash", "command": "pytest"})
    assert isinstance(w2, asyncio.Future) and w2.done() and w2.result() is True
    # A different tool still asks.
    w3 = cb({"id": "s3", "tool": "delete_file", "command": "x"})
    assert not (isinstance(w3, asyncio.Future) and w3.done())
    tool_approvals.resolve("s3", False, "alice")
    assert await w3 is False
    # Another chat, or another user on the same chat id, still asks.
    other = tool_approvals.make_approval_cb("alice", "chat2")({"id": "s4", "tool": "bash"})
    assert not (isinstance(other, asyncio.Future) and other.done())
    tool_approvals.resolve("s4", False, "alice")
    await other
    bob = tool_approvals.make_approval_cb("bob", "chat1")({"id": "s5", "tool": "bash"})
    assert not (isinstance(bob, asyncio.Future) and bob.done())
    tool_approvals.resolve("s5", False, "bob")
    await bob
    tool_approvals.clear_session_allow("alice", "chat1")


@pytest.mark.asyncio
async def test_deny_with_remember_does_not_allowlist():
    tool_approvals.clear_session_allow("alice", "chat3")
    cb = tool_approvals.make_approval_cb("alice", "chat3")
    w = cb({"id": "d1", "tool": "bash"})
    tool_approvals.resolve("d1", False, "alice", remember=True)
    assert await w is False
    assert tool_approvals.session_allowed("alice", "chat3") == set()


def test_chat_route_forwards_approval_events_to_browser():
    """The chat route forwards only an allowlist of agent SSE event types. The
    approval events were missing from it, so the browser never rendered the
    prompt and every gated turn froze until the TTL auto-denied (2026-10-03)."""
    import pathlib
    import re
    src = pathlib.Path(__file__).resolve().parents[1].joinpath("routes", "chat_routes.py").read_text()
    m = re.search(r'elif data\.get\("type"\) in \((.*?)\):', src, re.S)
    assert m, "forwarded event-type tuple not found in chat_routes"
    forwarded = m.group(1)
    for ev in ("approval_required", "approval_resolved", "ask_user", "tool_start"):
        assert f'"{ev}"' in forwarded, ev
