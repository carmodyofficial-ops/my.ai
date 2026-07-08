"""Nightly knowledge-pack audit — the pack-side sibling of the skill audit.

Skills get tested and auto-fixed nightly (routes/skills_routes.run_scheduled_skill_audit);
knowledge packs had no equivalent, so stubs and stale content sat invisible for weeks.
This module audits a rotating batch of packs each night:

  * STRUCTURAL checks (no LLM): served-file presence, the hollow-content gate the
    live retriever applies (imported from coding_knowledge so the two can't drift),
    manifest validity + routing triggers, staleness by content mtime.
  * LLM REVIEW (utility model, optional): a strict reviewer judges the pack text
    for factual red flags, meta-text filler, and vagueness. Flag-only by design —
    packs are TRUSTED prompt context, so a small local model must never rewrite
    them silently; weak packs are reported for the operator instead.

State lives in data/knowledge_packs/.audit_state.json (per-pack audited_at =>
least-recently-audited rotation, like the skill audit). Each run rewrites
data/knowledge_packs/AUDIT_REPORT.md with the latest findings.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.coding_knowledge import _is_hollow, _PACKS

logger = logging.getLogger(__name__)

STATE_FILE = _PACKS / ".audit_state.json"
REPORT_FILE = _PACKS / "AUDIT_REPORT.md"
SERVED_FILES = ("knowledge.md", "reference.md")  # what the live retriever reads
STALE_DAYS = 180
_LLM_REVIEW_MAX_CHARS = 9000  # plenty for a pack; keeps the judge prompt bounded

_REVIEW_SYS = (
    "You are a strict technical reviewer auditing a reference 'knowledge pack' that "
    "gets injected into an AI assistant's prompt as trusted context. Judge the TEXT "
    "on: (1) factual red flags — anything that looks wrong, deprecated, or risky to "
    "teach; (2) filler — meta-text, prose that carries no actionable specifics; "
    "(3) vagueness — advice too generic to act on. Do NOT judge formatting taste.\n"
    "Answer in exactly this format:\n"
    "VERDICT: PASS or WARN or FAIL\n"
    "ISSUES:\n- <one line per concrete issue, or '- none'>"
)


# --------------------------------------------------------------------------- #
# structural audit (pure, no LLM — unit-testable)
# --------------------------------------------------------------------------- #

def structural_audit(pack_dir: Path) -> Dict[str, Any]:
    """Non-LLM checks for one pack dir. Returns {pack_id, served, issues, ...};
    a pack with no served file is invisible to the retriever — worst issue."""
    issues: List[str] = []
    served: Optional[str] = None
    text = ""
    for name in SERVED_FILES:
        f = pack_dir / name
        if f.exists():
            try:
                t = f.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if t and not _is_hollow(t):
                served, text = name, t
                break
            if t and _is_hollow(t) and served is None:
                issues.append(f"{name} exists but fails the hollow gate (<600 chars or stub markers) — never served")
    if served is None and not issues:
        issues.append("no knowledge.md/reference.md — pack is invisible to the retriever")

    manifest: Dict[str, Any] = {}
    mf = pack_dir / "manifest.json"
    if mf.exists():
        try:
            manifest = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            issues.append("manifest.json is unreadable/invalid JSON")
    else:
        issues.append("no manifest.json")
    if manifest:
        triggers = [t for t in (manifest.get("triggers") or []) if str(t).strip()]
        if not triggers:
            issues.append("manifest has no 'triggers' — discovery routing falls back to semantic-only")
        if not str(manifest.get("summary", "")).strip():
            issues.append("manifest has no summary")

    stale_days = None
    if served:
        try:
            age_s = time.time() - (pack_dir / served).stat().st_mtime
            stale_days = int(age_s // 86400)
            if stale_days >= STALE_DAYS:
                issues.append(f"content untouched for {stale_days}d (stale threshold {STALE_DAYS}d)")
        except OSError:
            pass

    return {
        "pack_id": pack_dir.name,
        "served": served,
        "chars": len(text),
        "stale_days": stale_days,
        "issues": issues,
        "text": text,
    }


def rotation_order(pack_ids: List[str], state: Dict[str, Any]) -> List[str]:
    """Least-recently-audited first; never-audited sort to the very front
    (same rotation contract as the nightly skill audit)."""
    return sorted(pack_ids, key=lambda p: state.get(p, {}).get("audited_at", -1.0))


def load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: Dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    except OSError:
        logger.warning("pack audit: could not persist %s", STATE_FILE)


# --------------------------------------------------------------------------- #
# LLM review lane
# --------------------------------------------------------------------------- #

async def _llm_review(pack_id: str, text: str, url: str, model: str,
                      headers: Optional[dict]) -> Dict[str, Any]:
    from src.llm_core import llm_call_async
    body = text[:_LLM_REVIEW_MAX_CHARS]
    out = await llm_call_async(
        url, model,
        [{"role": "system", "content": _REVIEW_SYS},
         {"role": "user", "content": f"PACK: {pack_id}\n\n{body}"}],
        temperature=0.1, max_tokens=500, headers=headers,
        prompt_type="pack_audit",
    )
    verdict = "WARN"
    low = (out or "").lower()
    for v in ("pass", "warn", "fail"):
        if f"verdict: {v}" in low:
            verdict = v.upper()
            break
    notes = [l.strip("- ").strip() for l in (out or "").splitlines()
             if l.strip().startswith("-") and "none" not in l.lower()]
    return {"verdict": verdict, "notes": notes[:8]}


# --------------------------------------------------------------------------- #
# nightly entry point
# --------------------------------------------------------------------------- #

async def run_scheduled_pack_audit(max_packs: int = 6, llm: bool = True) -> Dict[str, Any]:
    """Audit the least-recently-audited packs. Structural always; LLM review when a
    utility model resolves. Flags only — never rewrites pack content."""
    if not _PACKS.is_dir():
        return {"status": "skipped", "reason": f"{_PACKS} missing"}

    state = load_state()
    pack_ids = [p.name for p in sorted(_PACKS.iterdir()) if p.is_dir()]
    batch = rotation_order(pack_ids, state)[:max(1, int(max_packs))]

    url = model = headers = None
    if llm:
        try:
            from routes.skills_routes import _resolve_audit_models
            url, model, headers, _teacher = _resolve_audit_models(owner=None)
        except Exception as e:
            logger.info("pack audit: LLM lane off (%s) — structural only", e)

    results: List[Dict[str, Any]] = []
    for pid in batch:
        res = structural_audit(_PACKS / pid)
        text = res.pop("text", "")
        if url and model and res["served"] and text:
            try:
                res["review"] = await _llm_review(pid, text, url, model, headers)
            except Exception as e:
                logger.warning("pack audit: LLM review failed for %s: %s", pid, e)
        state.setdefault(pid, {})["audited_at"] = time.time()
        state[pid]["issues"] = res["issues"]
        state[pid]["verdict"] = (res.get("review") or {}).get("verdict")
        results.append(res)
        logger.info("pack audit: %s — %d issue(s)%s", pid, len(res["issues"]),
                    f", review {res['review']['verdict']}" if res.get("review") else "")

    save_state(state)
    _write_report(results, model)
    flagged = [r for r in results
               if r["issues"] or (r.get("review") or {}).get("verdict") == "FAIL"]
    return {"status": "done", "audited": len(results), "flagged": len(flagged),
            "results": results}


def _write_report(results: List[Dict[str, Any]], model: Optional[str]) -> None:
    lines = [
        "# Knowledge Pack Audit Report",
        f"_Last run: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"
        + (f" — reviewer model: {model}_" if model else " — structural checks only_"),
        "",
    ]
    for r in results:
        verdict = (r.get("review") or {}).get("verdict", "")
        mark = "🔴" if (verdict == "FAIL" or not r["served"]) else ("🟡" if (r["issues"] or verdict == "WARN") else "🟢")
        lines.append(f"## {mark} {r['pack_id']}  ({r['chars']} chars"
                     + (f", {r['stale_days']}d old" if r.get("stale_days") is not None else "") + ")")
        for i in r["issues"]:
            lines.append(f"- [structural] {i}")
        for n in (r.get("review") or {}).get("notes", []):
            lines.append(f"- [review/{verdict}] {n}")
        if not r["issues"] and not (r.get("review") or {}).get("notes"):
            lines.append("- clean")
        lines.append("")
    try:
        REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        logger.warning("pack audit: could not write %s", REPORT_FILE)
