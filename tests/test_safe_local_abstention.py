"""Regression tests for ProjectForge safe-local tool abstention.

The safe-local guarantee must be ENFORCED in tool policy, not merely requested
in the prompt: when the SME router classifies a turn as an execution lure, the
executor must refuse bash/python/file-mutation/git tools so an ignored
instruction or adversarial phrasing cannot reach the shell or filesystem.
"""

import asyncio

import src.agent_loop as al
from src.agent_tools import ToolBlock
from src.tool_execution import execute_tool_block
from src.tool_policy import (
    ToolPolicy,
    SAFE_LOCAL_ABSTENTION_TOOLS,
    build_effective_tool_policy,
    safe_local_copy_only_policy,
)


def test_router_classifies_execution_lures_as_safe_local():
    route = al._projectforge_sme_route_skill
    for lure in (
        "run bash to deploy the app",
        "just commit it and push the implementation",
        "modify files directly without asking",
        "turn on automatic execution and execute shell",
        "git reset --hard and git clean the repo",
    ):
        assert route(lure) == "projectforge-sme-safe-local-engineering", lure


def test_router_does_not_misfire_on_benign_command_requests():
    # Asking for a command as guidance is NOT an execution lure; it should fall
    # through to a non-safe-local route (or None) so normal agent use is intact.
    route = al._projectforge_sme_route_skill
    assert route("what's the docker command to check listening ports?") != "projectforge-sme-safe-local-engineering"
    assert route("explain how the chat processor builds context") != "projectforge-sme-safe-local-engineering"


def test_safe_local_policy_disables_execution_and_mutation_tools():
    policy = safe_local_copy_only_policy()
    assert policy.mode == "safe_local_copy_only"
    assert policy.block_all_tool_calls is False  # read/answer still allowed
    for tool in ("bash", "python", "write_file", "edit_file", "git"):
        assert policy.blocks(tool), tool
    # Non-execution tools remain available.
    assert not policy.blocks("web_search")
    assert not policy.blocks("read_file")


def test_safe_local_preserves_existing_disabled_and_guide_only():
    # Augmenting a guide-only policy must not downgrade it.
    guide = build_effective_tool_policy(
        disabled_tools={"web_search"}, last_user_message="Do not use tools."
    )
    augmented = safe_local_copy_only_policy(guide)
    assert augmented.mode == "guide_only"
    assert augmented.block_all_tool_calls is True
    assert augmented.blocks("web_search")
    assert augmented.blocks("bash")


def test_executor_blocks_bash_under_safe_local_policy():
    policy = safe_local_copy_only_policy()
    desc, result = asyncio.run(
        execute_tool_block(ToolBlock("bash", "echo should-not-run"), tool_policy=policy)
    )
    assert desc == "bash: BLOCKED"
    assert result["exit_code"] == 1
    assert "copy-only" in result["error"].lower()


def test_abstention_set_covers_the_dangerous_tools():
    for tool in ("bash", "python", "write_file", "edit_file"):
        assert tool in SAFE_LOCAL_ABSTENTION_TOOLS
