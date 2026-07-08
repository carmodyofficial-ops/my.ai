#!/usr/bin/env python3
"""Create or validate a knowledge pack that the LIVE retriever will actually serve.

The retriever (src/coding_knowledge.py) only serves a pack when:
  * its dir name avoids the discovery skip-list substrings (guard/policy/etc.),
  * knowledge.md (or reference.md) exists and passes the hollow gate (>=600 chars,
    no stub markers),
  * manifest.json carries `triggers` (the primary routing signal for
    non-allowlisted packs).
Packs violating any of these sit invisible — this script refuses to create them.

Usage:
  # create (content from a file; refuses to overwrite without --force)
  python scripts/create_knowledge_pack.py my_new_pack \
      --name "My New Pack" --summary "One sentence." \
      --triggers "keyword one,keyword two,..." --content-file draft.md

  # validate an existing pack (also used by the nightly audit's standards)
  python scripts/create_knowledge_pack.py my_pack --check
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.coding_knowledge import _is_hollow  # single source of truth for the gate

PACKS = ROOT / "data/knowledge_packs"
# Mirror of coding_knowledge._DISCOVERY_SKIP_SUBSTR — ids matching these are
# never auto-served, so creating a content pack under such a name is a footgun.
SKIP_SUBSTR = ("guard", "policy", "_contract", "abstention", "protocol",
               "k2t_", "k2r_", "rubric", "system_architecture", "runbook")
MIN_TRIGGERS = 6


def validate(pack_dir: Path) -> list[str]:
    """Return a list of problems (empty == pack will serve)."""
    problems: list[str] = []
    pid = pack_dir.name
    if any(s in pid for s in SKIP_SUBSTR):
        problems.append(f"pack id '{pid}' matches a discovery skip-list substring — will never auto-serve")

    served = None
    for name in ("knowledge.md", "reference.md"):
        f = pack_dir / name
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="replace").strip()
            if text and not _is_hollow(text):
                served = name
                break
            problems.append(f"{name} fails the hollow gate (<600 chars or stub markers)")
    if served is None and not any("hollow" in p for p in problems):
        problems.append("no knowledge.md or reference.md")

    mf = pack_dir / "manifest.json"
    if not mf.exists():
        problems.append("no manifest.json")
    else:
        try:
            man = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"manifest.json invalid JSON: {e}")
            man = {}
        if man:
            triggers = [t for t in (man.get("triggers") or []) if str(t).strip()]
            if len(triggers) < MIN_TRIGGERS:
                problems.append(f"manifest needs >= {MIN_TRIGGERS} triggers (has {len(triggers)}) — "
                                "triggers are the primary routing signal")
            if any(t != t.lower() for t in triggers):
                problems.append("triggers must be lowercase (matching is against a lowercased query)")
            if not str(man.get("summary", "")).strip():
                problems.append("manifest has no summary")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pack_id", help="snake_case directory name under data/knowledge_packs/")
    ap.add_argument("--check", action="store_true", help="validate an existing pack and exit")
    ap.add_argument("--name", help="human-readable pack name")
    ap.add_argument("--summary", help="one-sentence summary")
    ap.add_argument("--triggers", help="comma-separated lowercase routing keywords (>=6)")
    ap.add_argument("--topics", default="", help="comma-separated topic words")
    ap.add_argument("--content-file", help="markdown file to install as knowledge.md")
    ap.add_argument("--force", action="store_true", help="overwrite an existing pack")
    args = ap.parse_args()

    pack_dir = PACKS / args.pack_id

    if args.check:
        if not pack_dir.is_dir():
            print(f"FAIL: {pack_dir} does not exist")
            return 1
        problems = validate(pack_dir)
        if problems:
            print(f"FAIL: {args.pack_id}")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"OK: {args.pack_id} will serve")
        return 0

    # ---- create mode ----
    missing = [f for f in ("name", "summary", "triggers", "content_file") if not getattr(args, f)]
    if missing:
        ap.error(f"create mode requires --{', --'.join(m.replace('_', '-') for m in missing)}")
    if pack_dir.exists() and not args.force:
        ap.error(f"{pack_dir} already exists (use --force to overwrite)")

    content = Path(args.content_file).read_text(encoding="utf-8")
    if _is_hollow(content):
        ap.error("content fails the hollow gate (>=600 chars, no stub markers) — the retriever would never serve it")

    triggers = [t.strip().lower() for t in args.triggers.split(",") if t.strip()]
    if len(triggers) < MIN_TRIGGERS:
        ap.error(f"need >= {MIN_TRIGGERS} triggers; got {len(triggers)}")

    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "knowledge.md").write_text(content, encoding="utf-8")
    manifest = {
        "name": args.name,
        "pack_id": args.pack_id,
        "trust_level": "high",
        "guarded": False,
        "triggers": triggers,
        "topics": [t.strip() for t in args.topics.split(",") if t.strip()] or triggers[:6],
        "summary": args.summary,
        "source": "authored",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    problems = validate(pack_dir)
    if problems:
        print(f"CREATED WITH WARNINGS: {args.pack_id}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: created {args.pack_id} — it will serve on the next query (discovery cache keys on mtime)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
