"""Regression tests for the completion-verifier / strong-judge machinery
(2026-07-04) and the honest run_tests signals that support it.

Locks in behaviors that were found broken live:
  - the actions snapshot crashed on dict-shaped file-tool diffs (AttributeError
    killed the cowork stream at the done-gate and cancelled the judge call);
  - a verdict-less (truncated) judge response silently parsed as a pass;
  - run_tests reported "exit 1"/ok=false for a test-less workspace, sending
    weak models into pointless re-verify loops;
  - guide-only explicit [TOOL_CALL] markup recovery (blocked tool_output) —
    coverage was lost when the ambiguous-fenced tests were updated for f46f4fb.
"""

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

import src.agent_loop as al


# ---------------------------------------------------------------------------
# _build_actions_snapshot — diff shapes
# ---------------------------------------------------------------------------

def _ev(**kw):
    base = {"tool": "edit_file", "command": "f.py", "output": "Edited f.py", "exit_code": 0}
    base.update(kw)
    return base


def test_snapshot_extracts_text_from_dict_diff():
    snap = al._build_actions_snapshot([
        _ev(diff={"text": "--- a/f.py\n+++ b/f.py\n-old\n+new", "added": 1, "removed": 1}),
    ])
    assert "+new" in snap and "-old" in snap


def test_snapshot_passes_through_string_diff():
    snap = al._build_actions_snapshot([_ev(diff="plain unified diff text")])
    assert "plain unified diff text" in snap


def test_snapshot_tolerates_missing_or_empty_diff():
    snap = al._build_actions_snapshot([_ev(), _ev(diff=None), _ev(diff={})])
    assert "Edited f.py" in snap


def test_snapshot_truncates_long_diffs():
    snap = al._build_actions_snapshot([_ev(diff={"text": "x" * 5000})])
    assert len(snap) < 5000
    assert "…" in snap


# ---------------------------------------------------------------------------
# _run_verifier_subagent — verdict parsing (fail-safe + observable)
# ---------------------------------------------------------------------------

def _run_verifier_with_response(monkeypatch, response):
    async def _fake_llm(**kwargs):
        if isinstance(response, Exception):
            raise response
        return response

    import src.llm_core as llm_core
    monkeypatch.setattr(llm_core, "llm_call_async", _fake_llm)
    return asyncio.run(al._run_verifier_subagent(
        "fix the bug", "[edit_file] f.py\n-> Edited",
        endpoint_url="http://x/v1/chat/completions", model="judge", headers={},
    ))


def test_verifier_success_verdict_returns_no_flags(monkeypatch):
    assert _run_verifier_with_response(
        monkeypatch, "Looks right.\nVERIFICATION: SUCCESS") == []


def test_verifier_fail_verdict_returns_semicolon_reasons(monkeypatch):
    flags = _run_verifier_with_response(
        monkeypatch,
        "Reasoning.\nVERIFICATION: FAIL: did not fix the bug; no changes made")
    assert flags == ["did not fix the bug", "no changes made"]


def test_verifier_verdictless_response_is_failsafe_pass(monkeypatch):
    # A truncated / reasoning-only response has no VERIFICATION line — it must
    # pass (never block a valid completion) but not crash.
    assert _run_verifier_with_response(monkeypatch, "…rambling reasoning cut off") == []


def test_verifier_llm_error_is_failsafe_pass(monkeypatch):
    assert _run_verifier_with_response(monkeypatch, RuntimeError("cold model")) == []


def test_verifier_ignores_think_blocks(monkeypatch):
    flags = _run_verifier_with_response(
        monkeypatch,
        "<think>VERIFICATION: FAIL: fake inner</think>\nVERIFICATION: SUCCESS")
    assert flags == []


# ---------------------------------------------------------------------------
# _model_is_strong — judge eligibility
# ---------------------------------------------------------------------------

def _patch_settings(monkeypatch, values):
    import src.settings as settings
    monkeypatch.setattr(settings, "get_setting",
                        lambda key, default=None: values.get(key, default))


def test_remote_api_models_are_strong(monkeypatch):
    assert al._model_is_strong("https://api.anthropic.com/v1", "claude-x") is True


def test_small_local_model_is_weak(monkeypatch):
    _patch_settings(monkeypatch, {"auto_model_complex": "big-model:120b"})
    assert al._model_is_strong("http://localhost:11434/v1", "qwen3-coder:30b") is False


def test_configured_complex_local_model_is_strong(monkeypatch):
    _patch_settings(monkeypatch, {"auto_model_complex": "big-model:120b"})
    assert al._model_is_strong("http://localhost:11434/v1", "big-model:120b") is True


def test_large_model_tag_is_strong_without_setting(monkeypatch):
    _patch_settings(monkeypatch, {"auto_model_complex": ""})
    assert al._model_is_strong("http://localhost:11434/v1", "llama-70b") is True


# ---------------------------------------------------------------------------
# run_tests — honest signals
# ---------------------------------------------------------------------------

def _run_tests_with(monkeypatch, *, rc, output):
    from src.agent_tools import coding_tools as ct

    async def _fake_run(cmd, cwd, ctx, timeout):
        return output, "", rc, False, timeout

    monkeypatch.setattr(ct, "_run", _fake_run)
    monkeypatch.setattr(ct, "_detect_test_framework", lambda cwd: "pytest")
    monkeypatch.setattr(ct.shutil, "which", lambda name: "/usr/bin/" + name)
    import src.tool_execution as te
    monkeypatch.setattr(te, "agent_cwd", lambda: "/tmp", raising=False)
    return asyncio.run(ct.RunTestsTool().execute("{}", {}))


def test_run_tests_no_tests_collected_is_neutral(monkeypatch):
    res = _run_tests_with(monkeypatch, rc=5, output="no tests ran in 0.01s")
    assert res["ok"] is True and res.get("no_tests") is True
    assert "no tests found" in res["summary"]


def test_run_tests_missing_pytest_is_clear_env_error(monkeypatch):
    res = _run_tests_with(monkeypatch, rc=1,
                          output="/usr/bin/python3: No module named pytest")
    assert res["ok"] is False and res.get("no_tests") is True
    assert "not installed" in res["error"]


def test_run_tests_real_failure_still_fails(monkeypatch):
    res = _run_tests_with(monkeypatch, rc=1, output="1 failed, 3 passed")
    assert res["ok"] is False
    assert res["failed"] == 1 and res["passed"] == 3


# ---------------------------------------------------------------------------
# coding_knowledge — budget override + discovery skip-gates
# ---------------------------------------------------------------------------

def test_knowledge_budget_override_caps_block():
    from src import coding_knowledge as ck
    if not ck._PACKS.is_dir():
        pytest.skip("knowledge packs not present in this checkout")
    q = "write a fastapi endpoint with dependency injection and a pytest for it"
    full = ck.coding_knowledge_block(q)
    small = ck.coding_knowledge_block(q, max_total_chars=2800)
    if not full:
        pytest.skip("no packs matched in this checkout")
    assert len(small) <= 2900
    assert len(small) <= len(full)


def test_discovery_never_serves_internal_system_packs():
    from src import coding_knowledge as ck
    if not ck._PACKS.is_dir():
        pytest.skip("knowledge packs not present in this checkout")
    served = {e["id"] for e in ck._discovered_entries()}
    for banned in ("odysseus_system_architecture", "ops_runbook_and_incident_response",
                   "auth_and_guest_access_model", "my_ai_system_core"):
        assert banned not in served
    # guard/policy families are skipped by substring
    assert not any("guard" in pid or "runbook" in pid or "system_architecture" in pid
                   for pid in served)


# ---------------------------------------------------------------------------
# guide-only: explicit [TOOL_CALL] markup still parses and is BLOCKED with an
# explicit tool_output (the recovery path; ambiguous fenced blocks are content)
# ---------------------------------------------------------------------------

def _collect(gen):
    async def _run():
        return [c async for c in gen]
    return asyncio.run(_run())


def _events(chunks):
    out = []
    for chunk in chunks:
        if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
            try:
                out.append(json.loads(chunk[6:]))
            except Exception:
                pass
    return out


def test_guide_only_blocks_explicit_tool_call_markup(monkeypatch):
    from src.tool_policy import build_effective_tool_policy

    monkeypatch.setattr(al, "get_setting", lambda key, default=None: default, raising=False)
    monkeypatch.setattr(al, "get_mcp_manager", lambda: None, raising=False)
    monkeypatch.setattr(al, "estimate_tokens", lambda *a, **k: 10, raising=False)

    async def _fake_stream(_candidates, messages, **kwargs):
        yield "data: " + json.dumps(
            {"delta": '[TOOL_CALL] {tool: "bash", command: "echo should-not-run"} [/TOOL_CALL]'}
        ) + "\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(al, "stream_llm_with_fallback", _fake_stream, raising=False)

    policy = build_effective_tool_policy(
        last_user_message="GUIDE-ONLY MODE. DO NOT USE TOOLS.")
    chunks = _collect(al.stream_agent_loop(
        "http://local.test/v1", "local-model",
        [{"role": "user", "content": "GUIDE-ONLY MODE. DO NOT USE TOOLS."}],
        max_rounds=1, relevant_tools={"bash"}, tool_policy=policy,
    ))
    events = _events(chunks)
    outputs = [e for e in events if e.get("type") == "tool_output"]
    # Explicit markup is unmistakably a tool call: it must surface as a blocked
    # tool result (not silent, not executed).
    assert outputs, "expected a blocked tool_output for explicit [TOOL_CALL] markup"
    blocked = outputs[0]
    assert blocked.get("exit_code") == 1
    assert "not executed" in str(blocked.get("output") or "")
    # and nothing actually ran
    assert not any(e.get("exit_code") == 0 for e in outputs)
