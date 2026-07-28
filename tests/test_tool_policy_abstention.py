"""Safe-local (copy-only) turns must not be able to touch the host.

`SAFE_LOCAL_ABSTENTION_TOOLS` is the mechanical half of the ProjectForge
copy-only guarantee — the prompt also asks the model to abstain, but prose is
not a guard. The set had only `write_file`/`edit_file`, so a copy-only turn
could still mutate the filesystem through `multi_edit`, `apply_patch`,
`delete_file` or `move_file`, and still execute code through `code_sandbox` or
`run_tests`. These tests pin the whole surface so a newly added execution or
mutation tool cannot silently reopen the hole.
"""
from src.tool_policy import SAFE_LOCAL_ABSTENTION_TOOLS


def test_all_file_mutation_tools_are_withheld():
    for tool in ("write_file", "edit_file", "multi_edit", "apply_patch",
                 "delete_file", "move_file"):
        assert tool in SAFE_LOCAL_ABSTENTION_TOOLS, (
            f"{tool} mutates files but is not withheld on a copy-only turn"
        )


def test_all_execution_tools_are_withheld():
    for tool in ("bash", "python", "code_sandbox", "run_tests", "git",
                 "lint_format"):
        assert tool in SAFE_LOCAL_ABSTENTION_TOOLS, (
            f"{tool} executes code but is not withheld on a copy-only turn"
        )


def test_read_only_tools_are_not_withheld():
    """Abstention must not blind the agent — it can still look, just not touch."""
    for tool in ("read_file", "grep", "glob", "ls", "get_workspace",
                 "web_search", "web_fetch"):
        assert tool not in SAFE_LOCAL_ABSTENTION_TOOLS, (
            f"{tool} is read-only and should stay available on a copy-only turn"
        )


def test_every_registered_mutating_tool_is_covered():
    """Catch a NEW execution/mutation tool that forgets to join the set.

    Uses the real handler registry so adding e.g. `truncate_file` without
    updating SAFE_LOCAL_ABSTENTION_TOOLS fails here rather than in production.
    """
    from src.agent_tools import TOOL_HANDLERS

    # Tools whose names imply host mutation or execution.
    suspicious = {
        name for name in TOOL_HANDLERS
        if any(k in name for k in ("write", "edit", "delete", "move", "patch",
                                   "bash", "python", "sandbox", "exec", "run"))
    }
    # Document-panel tools operate on app documents, not host files.
    suspicious -= {"edit_document", "update_document", "create_document",
                   "suggest_document", "manage_documents"}
    missing = sorted(suspicious - set(SAFE_LOCAL_ABSTENTION_TOOLS))
    assert not missing, (
        "these host-mutating/executing tools are not withheld on a copy-only "
        f"turn: {missing}"
    )
