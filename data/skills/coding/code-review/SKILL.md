---
name: code-review
description: "How to review code for what actually matters: correctness and edge cases first, then security and resource handling, then tests, then style — with concrete red flags to look for."
version: 1.0.0
category: Coding
tags: [code-review, review, critique, pr, pull-request, audit, correctness, bug, security, red-flags, diff, assess, feedback]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when reviewing a diff, a pull request, or a piece of code for issues. Prioritize finding real defects over style nits; report the highest-severity problems first.

## Procedure

1. Understand the intent first: what is this change supposed to do? Review against that, and read the surrounding code so you can tell whether it fits the existing conventions.
2. Correctness pass (highest priority). Trace the logic for the happy path AND the edges: empty/None/zero/one/max inputs, off-by-one at boundaries, error paths, concurrency/ordering, and the cases the author probably didn't test. Does it actually do what it claims?
3. Security & safety pass: unparameterized SQL / shell / `eval` (injection), unvalidated external input, secrets in code/logs, missing authz checks, path traversal, untrusted data treated as trusted. Flag these as high severity.
4. Resource & failure pass: unclosed files/connections/locks, unbounded loops/memory, missing timeouts on network calls, swallowed exceptions (`except: pass`), N+1 queries, blocking calls on a hot/async path.
5. Tests & verifiability: is the new behavior covered by a test? Does the test actually fail if the code is wrong? Did the author verify it (or just claim it works)?
6. Then style/maintainability (lowest priority): naming, dead code, overly large functions, leaky abstractions, convention mismatches. Don't let nits bury a real bug.
7. Report findings by severity (correctness/security first), each with file:line, why it's wrong, and a concrete fix. Acknowledge what's good. Be specific, not vague.

## Pitfalls

- Leading with style nits while a correctness or security bug goes unmentioned.
- Approving because it "looks right" without tracing the edge cases.
- Vague feedback ("this could be cleaner") instead of a specific issue + fix.
- Reviewing the diff in isolation, missing that it breaks a caller or an invariant elsewhere — check the call sites.
- Trusting "tests pass" without checking the tests actually exercise the change.

## Verification

- You traced the happy path and the edge/error cases, not just read it.
- You explicitly checked injection, input validation, secrets, and resource handling.
- Findings are ordered by severity, each with file:line and a concrete fix.
