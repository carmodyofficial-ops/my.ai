---
name: repo-diagnostics
description: "How to orient in an unfamiliar or changed repo: map structure, read git state, locate the relevant code, and find likely defects BEFORE editing — so changes are grounded in how the code actually works."
version: 1.0.0
category: Coding
tags: [repo, codebase, orient, diagnose, investigate, what changed, git status, find the bug, unfamiliar code, understand, locate]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use before editing an unfamiliar codebase, when a feature/bug spans files you don't yet know, or when you need to understand what recently changed and why something broke.

## Procedure

1. Orient on structure first: top-level layout, language(s), entry points (main/app/index), build/test config. Read the README and any CLAUDE.md/AGENTS.md before diving in.
2. Read the git state — it's the fastest signal: `git status` (uncommitted work), `git log --oneline -15` (recent direction), `git diff` (what's in flight). A recent commit often points straight at a regression. Use the `git` tool, not freehand shell.
3. Locate the relevant code by the symptom, not by guessing: `grep` the error string verbatim, the feature's user-facing label, or the function/route name; `glob` for the file naming convention. Read the actual matches, not just the file list.
4. Trace ONE real path end-to-end through the system (request → handler → data → response) instead of skimming many files. Understanding one path beats half-reading ten.
5. Check the tests for the area — they document intended behavior and give you a reproduction harness. Run the scoped tests (`run_tests` with a path) to see current state.
6. Form an explicit hypothesis ("the regression is in X because Y"), then confirm it with evidence before changing anything. State assumptions and what you still need to verify.

## Pitfalls

- Editing before understanding — the #1 cause of wrong fixes.
- Ignoring git history when a recent commit caused the issue (`git log`/`git diff` would have shown it).
- Grepping too broadly and drowning in matches — search the specific symptom.
- Half-reading many files instead of tracing one path fully.
- Not running the existing tests first, so you don't know the baseline.

## Verification

- You can name the entry point, the relevant files, and the one path you traced.
- Your hypothesis about the defect is backed by a grep hit / git diff / failing test, not a guess.
- You ran the scoped tests to establish the baseline before editing.
