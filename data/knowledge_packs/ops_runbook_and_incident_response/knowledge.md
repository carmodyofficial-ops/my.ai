# Ops Runbook and Incident Response

Purpose: Help the AI operate my.ai like a local production system.

Common checks:
- `git status --short`
- `docker compose ps`
- `docker compose logs --tail`
- HTTP root check: 302 may be expected when unauthenticated.
- `/login` should return 200.
- `/api/auth/status` should report auth state.
- LAN URL: `http://<LAN_IP>:7000`

Interpretation:
- HTTP 200 login page: service reachable.
- HTTP 302 root: unauthenticated redirect; often healthy.
- HTTP 403 admin route as Guest: correct.
- HTTP 000: service unreachable, starting, wrong bind, or network issue.
- Shell errors after pasted logs often indicate terminal input contamination, not app failure.

Incident response:
1. Preserve evidence.
2. Identify whether failure is code, runtime, network, auth, or operator paste.
3. Stop making changes if auth/security is at risk.
4. Back up auth/session files before auth modifications.
5. Prefer rollback to last known good commit if live app breaks.
6. Record status after resolution.
