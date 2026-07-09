# K2T Terminal Debugging Precision Contract

Purpose: improve terminal debugging, ops, and engineering evidence answers.

Required terminal/debugging structure:
1. State observed output.
2. Classify status: PASS / REVIEW / FAIL.
3. Explain what each output line proves.
4. Explain what is not proven.
5. Give safe next command.
6. Give expected output.
7. Give branch decision.
8. Warn what not to restart or mutate.
9. Provide rollback if changing state.

Command guidance:
- Prefer read-only inspection before mutation.
- Use `git status --short`, `git log -1 --oneline`, `jq`, `systemctl --user status`, `docker ps`, `curl -s -o /dev/null -w`.
- Avoid broad restarts during benchmark/model runs.
- Do not claim a service is healthy from process existence alone; verify HTTP/status behavior.
- Do not claim LAN access works from localhost-only checks.
- Do not claim retrieval works from metadata alone; run retrieval smoke.

A 4.75+ terminal answer should include:
- exact command
- why it is safe
- expected output
- interpretation
- next branch if it fails
