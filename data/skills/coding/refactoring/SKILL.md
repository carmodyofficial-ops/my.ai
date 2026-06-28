---
name: refactoring
description: "How to refactor safely: behavior-preserving changes in small steps with tests green between each, so you improve structure without introducing bugs."
version: 1.0.0
category: Coding
tags: [refactor, refactoring, restructure, clean up, extract, rename, simplify, technical debt, code smell, improve code]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when improving the structure of working code (extract a function, rename, dedupe, split a class, simplify a conditional) WITHOUT changing what it does — distinct from adding behavior.

## Procedure

1. Make sure tests are green first. No tests covering the code? Add a characterization test that pins the CURRENT behavior before you touch anything.
2. Separate refactor from feature. Never mix a behavior change into a refactor commit — both become unreviewable. One concern per commit.
3. Work in small, behavior-preserving steps, running the tests after each: rename, then extract, then inline, then move — not all at once. If a step goes red, you know exactly which one.
4. Use the safe sequence for common moves: extract function (select → name → replace duplicates), rename (one symbol, update all refs), replace conditional with table/dispatch, introduce a parameter object for a long signature.
5. Prefer deleting over abstracting. The simplest refactor is removing dead code, duplication-by-coincidence, and needless indirection. Don't abstract before the third duplication (rule of three).
6. Commit each green step (or stage them) so you can bisect/revert a single move if a later one breaks something.

## Pitfalls

- Refactoring with no tests and no characterization test — you can't tell if you preserved behavior.
- A giant "cleanup" diff mixing rename + extract + logic change — impossible to review or bisect.
- Creating the wrong abstraction; a leaky base class costs more than a little duplication.
- Reformatting unrelated lines, hiding the real change.
- "Refactoring" that quietly changes behavior (an edge case, an error path) — that's a bug, not a refactor.

## Verification

- Tests are green before AND after, and were run between steps.
- The diff is behavior-preserving; no feature/logic change rode along.
- The code is simpler (fewer cases, clearer names), not just rearranged.
