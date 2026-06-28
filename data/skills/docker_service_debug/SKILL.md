---
name: docker-service-debug
description: "How to diagnose a local service/container that's down, unhealthy, or unreachable: read status and logs FIRST, isolate app-vs-network, and never blindly restart (it destroys the evidence and running state)."
version: 1.0.0
category: Coding
tags: [docker, container, service, debug, down, unhealthy, unreachable, logs, port, health check, compose, restart, 502, connection refused]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when a local container/service is crashed, restarting, unhealthy, or unreachable (connection refused, 502, timeouts) — and you need the cause, not a guess.

## Procedure

1. Read state before touching anything: `docker ps -a` (is it up, restarting, exited? what exit code?), `docker compose ps`. A crash-looping container has a story in its logs — don't restart it away.
2. Read the logs FIRST: `docker logs --tail 100 <name>` (and `--since 10m`). The actual error/traceback is almost always here; restarting before reading destroys it.
3. Isolate app-vs-network: if the process is up but unreachable, check the port mapping (`docker port <name>`), then probe loopback (`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<port>/`). App-up + port-unreachable ⇒ networking/binding, not app logic.
4. Inspect from inside when needed: `docker exec <name> <cmd>` to check config, env (without printing secrets), file perms, or whether the app bound to 0.0.0.0 vs 127.0.0.1.
5. Form a hypothesis from the evidence (bad config / missing dep / port clash / OOM-kill / permission) and fix the CAUSE.
6. Restart only as the deliberate last step, and for this system, only with operator approval — a restart kills running exec processes and in-flight work, and recreate can change exposure. Never change LAN/port exposure to "fix" reachability without approval.

## Pitfalls

- Restarting before reading logs — erases the evidence and the running state.
- Assuming it's the app when the process is healthy but the port/binding is wrong.
- Printing secrets/.env while inspecting config.
- `compose down`/recreate that drops state or changes exposure, done reflexively.
- Treating a transient OOM-kill as an app bug (check exit code 137 / dmesg).

## Verification

- You read `docker ps`/status and the logs before any mutating action.
- The cause is identified from evidence (a log line, an exit code, a failed loopback probe), not assumed.
- Any restart/recreate was the last resort, safe, and (for this system) operator-approved; exposure unchanged.
