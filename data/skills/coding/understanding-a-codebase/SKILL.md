---
name: understanding-a-codebase
description: "How to quickly orient in an unfamiliar codebase: find the entry points, map the structure, learn the conventions, and trace a feature end-to-end before changing anything."
version: 1.0.0
category: Coding
tags: [codebase, explore, understand, orient, unfamiliar, navigate, read-code, project-structure, conventions, trace, where-is, how-does, find]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when starting work in a project you don't know yet, or before changing code whose surrounding context you haven't mapped. The goal is to understand enough to make a correct, convention-matching change — fast.

## Procedure

1. Get the shape first. `ls` the root; read README, package.json/pyproject.toml/requirements, and the main entry point (`app.py`, `main.*`, `index.*`). These tell you the language, framework, how it runs, and the top-level layout.
2. Map the directories. One `ls` per top-level dir to learn what lives where (routes/handlers, models, services, tests, static). Note the naming pattern — it predicts where new code should go.
3. Find the thing you care about with grep, not guessing. Search for the route path, the symbol, the error string, the UI label, or the function name. `grep` the literal first; it jumps you straight to the definition and its call sites.
4. Trace one feature end-to-end. Pick the closest existing feature to your task and follow it: entry point → handler → service/logic → data → response. Read the real signatures and types as you go. This teaches you the conventions (error handling, logging, config, how data flows) better than any doc.
5. Identify the conventions to copy: how are similar things registered/wired, how are errors raised/handled, how is config/auth accessed, how are tests written, what helpers already exist (grep before writing a new one).
6. Only now plan your change, placing it where the analogous code already lives and matching its patterns.

## Pitfalls

- Editing before reading the surrounding code or the analogous existing feature — you break an assumption you never saw.
- Guessing file locations instead of `grep`-ing for a known string/symbol.
- Reinventing a helper/util/pattern the repo already has (config loading, http client, error wrapper) — search first.
- Trusting a stale README/comment over the actual code; when they disagree, the code wins.
- Trying to understand the WHOLE repo; understand just the slice your change touches, plus its immediate conventions.

## Verification

- You can name the entry point, where your change goes, and the existing feature you patterned it on.
- You confirmed real signatures/types by reading them, not assuming.
- Your plan reuses existing helpers and matches the repo's conventions.
