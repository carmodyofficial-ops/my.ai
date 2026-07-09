# Engineering Quality Bar

Purpose: Define what good engineering behavior looks like.

Classification:
- PASS: Evidence proves acceptance criteria are met.
- REVIEW: Work may be correct but evidence is incomplete or caveated.
- FAIL: Test, compile, smoke, or logic failure.
- REJECTED: Unsafe/destructive/wrong-direction change even if partially working.

Standards:
- Cite concrete evidence from logs, tests, or diffs.
- Distinguish app failures from terminal paste mistakes.
- Do not ask for clarification when a safe best-effort path is obvious.
- Provide paste-safe commands.
- Explain remaining caveats.
- Always protect security and local-only constraints.
- Never treat “no output” as success unless the command semantics support it.
- Never claim tests passed when they were blocked or missing.

Patch expectations:
- Small.
- Reviewable.
- Targeted.
- Backed by regression tests.
- Backed by runtime smoke when applicable.
