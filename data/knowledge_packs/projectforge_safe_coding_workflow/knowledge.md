# ProjectForge Safe Coding Workflow

Purpose: Define how my.ai should safely make and validate code changes.

Principles:
- Prefer smallest safe patch.
- Avoid broad rewrites.
- Preserve existing behavior unless explicitly changing it.
- Never claim success without compile/test/smoke evidence.
- Treat destructive diffs as suspicious even if tests pass.
- Use explicit status classifications: PASS, REVIEW, FAIL, REJECTED.

Safe workflow:
1. Understand scope.
2. Identify protected paths.
3. Use safe mirror for UI/docs where applicable.
4. Generate patch.
5. Inspect diff.
6. Run compile checks.
7. Run targeted tests.
8. Run live smoke if behavior is runtime-visible.
9. Record status report.
10. Commit only after validation.

Important lessons:
- K2G v01 was rejected because it broadly rewrote theme CSS and removed existing markers/selectors.
- K2G v03 passed because it was additive and preserved semantic warning/error/destructive colors.
- K2L tests caught a real Guest admin-promotion defect before commit.

Protected areas:
- auth/session/security files
- .env/secrets/token files
- docker/compose/network exposure
- model routing
- memory/RAG stores
- data directories
