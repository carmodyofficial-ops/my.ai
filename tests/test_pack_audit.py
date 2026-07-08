"""Knowledge-pack audit — structural checks and rotation contract.

The nightly pack audit (src/pack_audit.py) mirrors the skill audit: rotate
through the least-recently-audited packs, flag structural problems the live
retriever silently punishes (hollow content never serves; a manifest without
`triggers` falls back to semantic-only routing). These tests pin the
non-LLM contract so pack authoring/tooling can rely on it.
"""

import json
import time

import pytest

from src.pack_audit import rotation_order, structural_audit
from src.coding_knowledge import _is_hollow


SUBSTANTIVE = "# T\n" + "\n".join(f"- fact {i}: `code_{i}` does a concrete thing" for i in range(30))


def _mk_pack(tmp_path, name, knowledge=None, manifest=None):
    d = tmp_path / name
    d.mkdir()
    if knowledge is not None:
        (d / "knowledge.md").write_text(knowledge, encoding="utf-8")
    if manifest is not None:
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return d


def _manifest(**over):
    m = {"name": "T", "pack_id": "t", "trust_level": "high", "guarded": False,
         "triggers": ["alpha", "beta", "gamma"], "summary": "s"}
    m.update(over)
    return m


def test_clean_pack_has_no_issues(tmp_path):
    d = _mk_pack(tmp_path, "good", SUBSTANTIVE, _manifest())
    res = structural_audit(d)
    assert res["served"] == "knowledge.md"
    assert res["issues"] == []


def test_hollow_content_is_flagged_and_not_served(tmp_path):
    d = _mk_pack(tmp_path, "stub", "tiny", _manifest())
    res = structural_audit(d)
    assert res["served"] is None
    assert any("hollow" in i for i in res["issues"])


def test_hollow_gate_matches_live_retriever(tmp_path):
    # The audit must use the SAME gate as coding_knowledge — a pack the audit
    # calls served must also pass the retriever's _is_hollow.
    d = _mk_pack(tmp_path, "edge", SUBSTANTIVE, _manifest())
    res = structural_audit(d)
    text = (d / "knowledge.md").read_text()
    assert (res["served"] is not None) == (not _is_hollow(text))


def test_stub_marker_fails_even_when_long(tmp_path):
    text = SUBSTANTIVE + "\nprocedures to expand later"
    d = _mk_pack(tmp_path, "marked", text, _manifest())
    res = structural_audit(d)
    assert res["served"] is None


def test_missing_triggers_flagged(tmp_path):
    d = _mk_pack(tmp_path, "no_trig", SUBSTANTIVE, _manifest(triggers=[]))
    res = structural_audit(d)
    assert any("triggers" in i for i in res["issues"])


def test_missing_manifest_flagged(tmp_path):
    d = _mk_pack(tmp_path, "no_man", SUBSTANTIVE)
    res = structural_audit(d)
    assert any("manifest" in i for i in res["issues"])


def test_invalid_manifest_json_flagged(tmp_path):
    d = _mk_pack(tmp_path, "bad_json", SUBSTANTIVE)
    (d / "manifest.json").write_text("{not json", encoding="utf-8")
    res = structural_audit(d)
    assert any("invalid JSON" in i for i in res["issues"])


def test_reference_md_serves_when_no_knowledge_md(tmp_path):
    d = _mk_pack(tmp_path, "ref_only", None, _manifest())
    (d / "reference.md").write_text(SUBSTANTIVE, encoding="utf-8")
    res = structural_audit(d)
    assert res["served"] == "reference.md"


def test_rotation_never_audited_first_then_oldest():
    state = {"b": {"audited_at": 100.0}, "c": {"audited_at": 50.0}}
    # 'a' never audited -> front; then 'c' (older) before 'b'
    assert rotation_order(["a", "b", "c"], state) == ["a", "c", "b"]


def test_rotation_is_stable_for_equal_timestamps():
    state = {"x": {"audited_at": 10.0}, "y": {"audited_at": 10.0}}
    assert rotation_order(["x", "y"], state) == ["x", "y"]


def test_stale_content_flagged(tmp_path):
    import os
    d = _mk_pack(tmp_path, "old", SUBSTANTIVE, _manifest())
    ancient = time.time() - 200 * 86400
    os.utime(d / "knowledge.md", (ancient, ancient))
    res = structural_audit(d)
    assert res["stale_days"] >= 199
    assert any("stale" in i for i in res["issues"])
