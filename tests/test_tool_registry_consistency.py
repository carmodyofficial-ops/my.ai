"""The four tool registries must agree.

Every tool is described in up to four independent places:

  * ``TOOL_HANDLERS``          (src/agent_tools/__init__.py) — name → implementation
  * ``TOOL_TAGS``              (src/agent_tools/__init__.py) — the ACCEPTANCE GATE for
                                both fenced blocks and native function calls
  * ``FUNCTION_TOOL_SCHEMAS``  (src/tool_schemas.py)         — what native models see
  * ``TOOL_SECTIONS``          (src/agent_loop.py)           — what fenced models see

Nothing kept them in sync, and they had drifted into real bugs:
  * ``tail_serve_output`` had a schema but no tag, so the model was told the
    tool existed while every native call was rejected as "Unknown function
    call" — a silently dead tool.
  * Several schemas have no fenced section, making those tools invisible to
    local (fenced-path) models even when the toolset advertises them.

These tests pin the invariants that actually break behaviour.
"""
import pytest

from src.agent_loop import TOOL_SECTIONS
from src.agent_tools import TOOL_HANDLERS, TOOL_TAGS
from src.tool_schemas import FUNCTION_TOOL_SCHEMAS


def _schema_names() -> set:
    out = set()
    for entry in FUNCTION_TOOL_SCHEMAS:
        fn = entry.get("function") if isinstance(entry, dict) else None
        if isinstance(fn, dict) and fn.get("name"):
            out.add(fn["name"])
    return out


def test_every_schema_is_accepted_by_the_tag_gate():
    """A tool the model can CALL must be a tool the dispatcher ACCEPTS.

    This is the invariant tail_serve_output violated: schema present, tag
    missing, every call silently rejected.
    """
    missing = sorted(_schema_names() - set(TOOL_TAGS))
    assert not missing, (
        "these tools have a function schema but no TOOL_TAGS entry, so native "
        f"calls to them are silently rejected: {missing}"
    )


def test_every_handler_is_accepted_by_the_tag_gate():
    missing = sorted(set(TOOL_HANDLERS) - set(TOOL_TAGS))
    assert not missing, (
        f"these tools have an implementation but no TOOL_TAGS entry: {missing}"
    )


def test_every_fenced_section_is_accepted_by_the_tag_gate():
    missing = sorted(set(TOOL_SECTIONS) - set(TOOL_TAGS))
    assert not missing, (
        "these tools are documented for fenced-path models but the parser will "
        f"not accept them: {missing}"
    )


# Tools that currently have a native schema but no fenced TOOL_SECTIONS entry.
# Fenced-path models (most local models on Ollama) therefore never learn they
# exist. This is real debt, not a desired state — the allowlist exists so the
# gap cannot GROW silently. Shrink it; do not add to it.
KNOWN_SCHEMA_WITHOUT_FENCED_SECTION = {
    # dispatch_subagents was documented for fenced models on 2026-07-29 — it is
    # deliberately absent from this list now, and the staleness test below keeps
    # it that way.
    "http_request", "manage_corpus",
    "request_sandbox_build", "trigger_research", "api_call", "edit_image",
    "adopt_served_model", "list_serve_presets", "serve_preset",
    "list_cookbook_servers",
}


def test_no_new_tools_are_invisible_to_local_models():
    undocumented = _schema_names() - set(TOOL_SECTIONS)
    new = sorted(undocumented - KNOWN_SCHEMA_WITHOUT_FENCED_SECTION)
    assert not new, (
        "these tools have a native schema but no fenced TOOL_SECTIONS entry, so "
        f"local fenced-path models cannot use them: {new}. Add a section, or add "
        "to KNOWN_SCHEMA_WITHOUT_FENCED_SECTION with a reason."
    )


def test_known_gap_list_is_not_stale():
    """If a gap gets fixed, drop it from the allowlist so it can't regress."""
    documented_now = sorted(KNOWN_SCHEMA_WITHOUT_FENCED_SECTION & set(TOOL_SECTIONS))
    assert not documented_now, (
        "these tools now HAVE a fenced section — remove them from "
        f"KNOWN_SCHEMA_WITHOUT_FENCED_SECTION: {documented_now}"
    )


def test_update_plan_description_does_not_contradict_the_todo_instruction():
    """`update_plan` works with or without an approved plan.

    Both descriptions used to say it had "no effect if there is no active
    plan", which flatly contradicted CODING_TODO_ADDENDUM telling the model to
    call it FIRST for any multi-step task — i.e. the tool doc told the model
    its own instruction was a no-op.
    """
    fenced = TOOL_SECTIONS.get("update_plan", "")
    schema = next(
        (e["function"]["description"] for e in FUNCTION_TOOL_SCHEMAS
         if e.get("function", {}).get("name") == "update_plan"),
        "",
    )
    for text in (fenced, schema):
        assert text, "update_plan must be documented in both registries"
        lowered = text.lower()
        assert "no effect if there is no active plan" not in lowered
        assert "does nothing if there's no active plan" not in lowered
