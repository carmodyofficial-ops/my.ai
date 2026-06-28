---
name: test-authoring
description: "Write effective, fast, deterministic tests (pytest/jest): test behavior not implementation, assert real outcomes, cover the edge cases, and keep tests independent and readable."
version: 1.0.0
category: Coding
tags: [testing, tests, pytest, unit-test, jest, vitest, coverage, assert, fixtures, parametrize, tdd, regression]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when adding tests for new or changed behavior, writing a regression test for a bug you fixed, or improving a weak suite. Good tests catch real breakage, run fast, and don't break when you refactor internals.

## Procedure

1. Match the project's test setup. Find the existing tests (`tests/`, `*_test.py`, `*.test.ts`), the runner (pytest/jest/vitest), and the conventions (fixtures, factories, naming). Reuse them; run the suite once to confirm it's green before you add to it.
2. Test behavior, not implementation. Assert on the function's return value / observable effect / API response — not on private internals or call counts. A good test survives a refactor that keeps behavior the same.
3. Cover the cases that matter: the happy path, the boundaries (empty, zero, one, max, None/null), and the failure modes (invalid input raises the right error; the error path is handled). One clear assertion focus per test.
4. Make each test independent and deterministic. No shared mutable state, no order dependence, no real network/clock/randomness — use fixtures, fakes, `freeze_time`, fixed seeds, `tmp_path`. Parametrize (`@pytest.mark.parametrize`) instead of copy-pasting near-identical tests.
5. Name tests for what they assert (`test_add_returns_sum`, `test_parse_rejects_empty`). Arrange–Act–Assert structure; keep each test short and readable so a failure name tells you what broke.
6. Run them. They must pass for the right reason — temporarily break the code to confirm the test actually fails (a test that passes against broken code tests nothing). Keep the suite fast.

## Pitfalls

- Asserting on internals/mocks so the test breaks on every refactor (brittle) — or asserting nothing meaningful (useless).
- Only testing the happy path; bugs live in the edges and error paths.
- Order-dependent or flaky tests (shared state, real time/network/randomness).
- A test that passes even when the code is wrong — always confirm it can fail.
- Over-mocking until the test no longer exercises real behavior.
- Giant tests asserting ten things; when one fails you can't tell which behavior broke.

## Verification

- New tests pass, and demonstrably FAIL when the target behavior is broken.
- They cover the happy path, the edges, and at least one failure mode.
- They are independent, deterministic, and fast; they follow the project's existing test conventions.
