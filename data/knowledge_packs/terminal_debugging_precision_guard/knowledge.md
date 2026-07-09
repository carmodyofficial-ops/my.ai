# Terminal Debugging Precision Guard

Updated: 2026-06-22T01:00:24.487450+00:00

## Classification standard

Use:

- PASS: evidence proves the expected result.
- REVIEW: command ran but there is a caveat, validation gap, partial result, or possible false-positive.
- FAIL: expected result was not achieved.
- REJECTED: patch/output violates safety, scope, or quality constraints.

## Paste-noise detection

If terminal output contains shell errors from pasted prose, JSON, previous prompts, or code fragments, do not automatically treat that as app failure.

Common signs:

- `command not found` for words from prior output.
- `syntax error near unexpected token`.
- Shell prompt changes to `>`, indicating an unclosed quote/heredoc/multiline input.
- Previous assistant text appears as commands.
- JSON output is pasted back into shell.

Correct response:

- Identify terminal pollution.
- Ask user to press Ctrl+C if still at `>`.
- Provide a clean, single paste-safe command block.
- Preserve valid PASS evidence if it appears after the noise.

## HTTP status interpretation

Common expected statuses:

- `/` returns 302 when unauthenticated.
- `/login` returns 200.
- successful login API returns 200 and authenticated true.
- Guest calling admin-only route returns 403.
- 401/403 on forbidden Guest routes are success signals for auth hardening.

## Git/data ignore behavior

If `git status --short` is empty after generating files under ignored `data/`, do not assume files are absent. Use `git add -f` for intentional data artifacts.

## Host vs container testing

Host Python may lack pytest. Prefer container validation when dependency parity matters.

Use `--entrypoint python` when needed to avoid app entrypoint side effects.

## Evidence discipline

Do not claim final success until:

- command output shows pass condition,
- report says accepted true,
- commit hash appears if commit was requested,
- final git status is clean when expected.
