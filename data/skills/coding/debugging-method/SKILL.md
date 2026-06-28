---
name: debugging-method
description: "Systematically find and fix a bug: reproduce it, read the actual error/traceback, isolate the real cause, apply the smallest fix, and verify the fix and that nothing else broke."
version: 1.0.0
category: Coding
tags: [debugging, bug, fix, error, traceback, stack-trace, exception, failing-test, broken, crash, regression]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when something is broken — an exception, a failing test, a crash, wrong output, or a regression. The aim is to fix the actual root cause with evidence, not to guess and shotgun changes.

## Procedure

1. Reproduce it first. Get a single, fast, deterministic command that triggers the failure (the failing test, a `python3 -c`, a curl, a script). If you can't reproduce it, you can't confirm a fix — narrow down until you can.
2. Read the ACTUAL error. Open the full traceback/log. The real failure is usually the LAST frame in your code (not the deepest library frame). Note the exact file:line, the exception type, and the message. Don't theorize past what the error says.
3. Form one specific hypothesis. "X is None here because Y didn't set it" — not "something's wrong with the data." Confirm it: `read_file` the file:line, `grep` for where the value is set/used, add a temporary print or assert, or run a one-liner that checks the assumption.
4. Isolate. If the cause isn't obvious, bisect: comment out / shrink to a minimal repro, check recent changes (`git diff`, `git log -p` on the file), or binary-search the input. Reduce until only the culprit remains.
5. Fix the cause, not the symptom. Make the smallest change that removes the root cause. Don't wrap it in a blanket try/except, don't loosen a test, don't special-case the one input — fix why it happened.
6. Verify. Re-run the exact repro: it must now pass. Then run the surrounding tests to confirm you didn't break anything else. Remove any temporary prints/asserts you added.

## Pitfalls

- Reading the deepest stack frame (inside a library) instead of the last frame in your own code.
- Guessing and changing several things at once — now you don't know what fixed it (or what you broke).
- "Fixing" by catching/suppressing the exception or weakening the assertion — the bug is still there.
- Not reproducing first, so you can't prove the fix worked.
- Off-by-one / None / type / encoding / timezone / async-await mistakes are common — check those explicitly.
- Forgetting to re-run the broader tests after the fix (regression check).

## Verification

- The original failing command/test now passes, run directly.
- The surrounding tests still pass (no new breakage).
- The fix addresses the root cause you identified with evidence, and is minimal.
- Temporary debug prints/asserts are removed.
