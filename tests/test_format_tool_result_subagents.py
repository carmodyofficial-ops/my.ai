"""format_tool_result must handle dispatch_subagents' list-valued ``results``.

Regression: it appended the list straight into ``parts`` and ``"\\n".join``
raised TypeError, killing every agent run that dispatched sub-agents.
"""
from src.tool_execution import format_tool_result


def _dispatch_result():
    return {
        "model": "qwen3.8-flash-next:iq4xs",
        "mode": "explorer",
        "workspace": "/host/project",
        "count": 2,
        "succeeded": 1,
        "failed": 1,
        "results": [
            {"index": 0, "task": "map the repo layout", "result": "src/ has 12 modules",
             "tools_used": ["bash"]},
            {"index": 1, "task": "find the tests", "error": "explorer failed: timeout"},
        ],
    }


def test_dispatch_subagents_result_formats_without_error():
    out = format_tool_result("dispatch_subagents: 2 subtask(s)", _dispatch_result())
    assert "**Sub-agent 1** — map the repo layout\nsrc/ has 12 modules" in out
    assert "**Sub-agent 2** — find the tests\n**Error:** explorer failed: timeout" in out
    # Summary fields still reach the model via the extra-data block.
    assert '"succeeded": 1' in out and '"failed": 1' in out


def test_string_results_unchanged():
    out = format_tool_result("list_sessions", {"results": "No sessions found."})
    assert out == "### list_sessions\nNo sessions found."
