"""dispatch_subagents: explorers run without a workspace, and junk output from a
sub-agent that couldn't do its piece comes back as an actionable error.

Regression (2026-10-18 coding test): with no workspace bound, sub-agents were
tool-less; the parent asked them to run pwd/git/ls and got back ".", a dangling
sentence, and tool-call markup written as text — all reported as "result".
"""
import asyncio
import json

import src.ai_interaction as ai


def _run(coro):
    return asyncio.run(coro)


def test_cannot_reply_becomes_error():
    e = ai._subagent_outcome(0, "run git log", "CANNOT: needs a shell")
    assert "result" not in e
    assert "needs a shell" in e["error"] and "yourself" in e["error"]


def test_fake_tool_call_markup_becomes_error():
    junk = "<tool_call>\n<function=Read>\n<parameter=file_path>\n/app/README.md\n</parameter>\n</function>\n</tool_call>"
    e = ai._subagent_outcome(2, "read the README", junk)
    assert "result" not in e and "tool it does not have" in e["error"]


def test_empty_or_punctuation_only_becomes_error():
    for junk in ("", ".", "  ...  "):
        e = ai._subagent_outcome(0, "t", junk)
        assert "result" not in e and "no findings" in e["error"]


def test_real_findings_pass_through_with_extras():
    e = ai._subagent_outcome(1, "find X", "X is validated in src/a.py:12", tools_used=["grep"])
    assert e == {"index": 1, "task": "find X", "tools_used": ["grep"],
                 "result": "X is validated in src/a.py:12"}


def test_long_findings_truncated():
    e = ai._subagent_outcome(0, "t", "a" * 7000)
    assert e["result"].endswith("(truncated)") and len(e["result"]) < 6100


def test_explorers_used_without_workspace(monkeypatch):
    calls = []

    async def fake_explorer(idx, task, *, url, model, headers, workspace, shared, owner):
        calls.append(workspace)
        return {"index": idx, "task": task, "result": "found it"}

    monkeypatch.setattr(ai, "_run_explorer", fake_explorer)
    monkeypatch.setattr(ai, "_explorers_enabled", lambda: True)
    monkeypatch.setattr(ai, "resolve_endpoint", lambda *a, **k: ("http://x/v1", "m", {}))
    out = _run(ai.do_dispatch_subagents(json.dumps({"tasks": ["a", "b"]})))
    assert out["mode"] == "explorer" and out["workspace"] is None
    assert calls == ["", ""] and out["succeeded"] == 2


def test_reasoning_fallback_flags_junk(monkeypatch):
    import src.llm_core as llm_core

    async def fake_call(url, model, messages, **kw):
        assert "CANNOT:" in messages[0]["content"]  # tool-less prompt says so
        return "."

    monkeypatch.setattr(llm_core, "llm_call_async", fake_call)
    monkeypatch.setattr(ai, "_explorers_enabled", lambda: False)
    monkeypatch.setattr(ai, "resolve_endpoint", lambda *a, **k: ("http://x/v1", "m", {}))
    out = _run(ai.do_dispatch_subagents(json.dumps({"tasks": ["run pwd"]})))
    assert out["mode"] == "reasoning" and out["failed"] == 1
    assert "no findings" in out["results"][0]["error"]


def _fake_loop(events, seen):
    async def loop(url, model, messages, **kw):
        seen.append((messages, kw))
        for ev in events:
            yield "data: " + json.dumps(ev) + "\n\n"
    return loop


def test_explorer_without_workspace_is_told_its_roots(monkeypatch):
    import src.agent_loop as agent_loop
    seen = []
    monkeypatch.setattr(agent_loop, "stream_agent_loop", _fake_loop([{"delta": "data/app.db is SQLite"}], seen))
    e = _run(ai._run_explorer(0, "find dbs", url="u", model="m", headers={}, workspace="", shared="", owner=None))
    system = seen[0][0][0]["content"]
    assert "No workspace is bound" in system and "ABSOLUTE paths" in system
    assert e["result"] == "data/app.db is SQLite"


def test_explorer_with_workspace_gets_no_roots_hint(monkeypatch):
    import src.agent_loop as agent_loop
    seen = []
    monkeypatch.setattr(agent_loop, "stream_agent_loop", _fake_loop([{"delta": "ok src/a.py:1"}], seen))
    _run(ai._run_explorer(0, "t", url="u", model="m", headers={}, workspace="/w", shared="", owner=None))
    assert "No workspace is bound" not in seen[0][0][0]["content"]


def test_explorer_rounds_exhausted_reports_it(monkeypatch):
    import src.agent_loop as agent_loop
    events = [{"type": "tool_start", "tool": "ls"}, {"type": "rounds_exhausted", "rounds": 6}]
    monkeypatch.setattr(agent_loop, "stream_agent_loop", _fake_loop(events, []))
    e = _run(ai._run_explorer(0, "t", url="u", model="m", headers={}, workspace="", shared="", owner=None))
    assert "result" not in e and "rounds without an answer" in e["error"]
    assert e["tools_used"] == ["ls"]


def test_cannot_line_after_preamble_becomes_error():
    text = ("Let me confirm what I do have access to:\n\n"
            "**CANNOT:** I have no shell tool, so I cannot run `pwd`.\n\nWhat I can do instead: ...")
    e = ai._subagent_outcome(0, "run pwd", text)
    assert "result" not in e and "I have no shell tool" in e["error"]


def test_word_cannot_inside_findings_is_not_an_error():
    e = ai._subagent_outcome(0, "t", "The parser cannot: handle tabs — see src/p.py:40")
    assert e["result"].startswith("The parser")
