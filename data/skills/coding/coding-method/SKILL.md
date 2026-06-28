---
name: coding-method
description: "How to implement, add, build, change, edit, write, or refactor code correctly: understand the existing code first, make the smallest change that fits its conventions, then verify it actually works before claiming done."
version: 1.0.0
category: Coding
tags: [coding, code, software-engineering, implement, add, build, change, edit, write, refactor, function, method, module, class, feature, file, fix, develop, python, javascript, typescript]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use whenever you are writing or changing code in a project — adding a feature, wiring something up, refactoring, or editing files. The goal is correct, minimal, convention-matching changes that you have verified, not plausible-looking code.

## Procedure

1. Understand before you touch anything. Use `ls`/`glob` to find the relevant files, `grep` to locate the symbol/route/function you'll change, and `read_file` to read the surrounding code. Confirm the real signatures, imports, types, and patterns — never assume an API.
2. Find the project's conventions and reuse them. How are similar things already done here (error handling, logging, config, tests, naming)? Match that. Reuse existing helpers/utilities instead of writing new ones; search for them first.
3. Decide the smallest change that fully does the job. Prefer extending an existing function/module over adding a new one. For non-trivial work, state the 2–4 concrete steps, then do them in order.
4. Make the edit. Use `edit_file` for changes to existing files (exact string replacement, shows a diff); `write_file` only for new files or a deliberate full rewrite. Keep the diff tight and focused on the request — don't drive-by reformat unrelated code.
5. Verify immediately. Byte-compile changed files (`python3 -m compileall -q <files>`), run the linter, and run the relevant tests (`pytest -q path::test`, `npm test`). Read the output. For a behavior change, actually exercise the new path.
6. Iterate until green. If a check fails, read the real error, fix the actual cause, re-run. Then re-read your final diff and remove anything stray (debug prints, dead code, TODOs you introduced).

## Pitfalls

- Editing a file you never read → `old_string` won't match, or you break an assumption you didn't see.
- Reinventing a helper that already exists in the repo — grep first.
- Big rewrites when a 3-line `edit_file` would do; large diffs are hard to review and easy to get wrong.
- Declaring success without running anything. "It should work" is not verification.
- Matching your own style instead of the file's (imports, quotes, error handling, async patterns).
- Leaving the tree half-edited between turns, or silencing a failing check instead of fixing it.

## Verification

- Changed files byte-compile / the build passes.
- Relevant tests pass; you added or updated a test if you changed behavior and a suite exists.
- The final diff is minimal, focused, and matches the surrounding code's conventions.
- You ran the actual code path at least once and saw the expected result.
