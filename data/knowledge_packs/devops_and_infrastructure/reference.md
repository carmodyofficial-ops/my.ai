# DevOps & Infra Cheat-Sheet

## Dockerfile
- Pin versions: `FROM python:3.12-slim`, not `:latest`. Reproducible builds.
- Layer order = cache: copy dep manifest, install, THEN copy source. Code changes won't bust the dep layer.
  ```
  COPY requirements.txt . && RUN pip install -r requirements.txt
  COPY . .
  ```
- Multi-stage: build in a fat image, `COPY --from=build /app/bin` into slim runtime. Ships no toolchain.
- Run non-root: `RUN useradd app && USER app`.
- `.dockerignore` `.git`, `node_modules`, `__pycache__` — smaller context, faster builds, no secret leaks.
- MISTAKE: secrets in `ARG`/`ENV` — they persist in layers. Mount or pass at runtime instead.

## docker-compose
- Bind mount (`./src:/app`) for live dev; named volume for DB/state persistence. Don't bind-mount over `node_modules`.
- Env: `env_file: .env`, gitignore it; commit `.env.example`.
- Healthcheck gates `depends_on: condition: service_healthy`:
  ```
  healthcheck:
    test: ["CMD","curl","-f","http://localhost:8080/health"]
    interval: 10s
    retries: 5
  ```
- `restart` reuses the container (keeps stale image); after a Dockerfile change use `up --build` to recreate.
- Ports `HOST:CONTAINER` — clashes mean host port taken, not the app.

## Debugging
- `docker logs -f <c>`; shell in: `docker exec -it <c> sh`.
- Change didn't apply? Code-mount edit needs a process restart; Dockerfile/dep edit needs a rebuild (stale image).

## Shell
- Start every script: `set -euo pipefail` — exit on error, unset var, pipe failure.
- Quote all expansions: `"$var"`, `"$@"` — spaces/globs break unquoted.
- Cleanup: `trap 'rm -f "$tmp"' EXIT`.
- `cmd || true` only where failure is genuinely fine.

## CI & Secrets
- Cache deps (`~/.cache/pip`, `node_modules`) keyed on lockfile hash; run fast/cheap checks (lint, unit) first for quick feedback.
- Never bake secrets into images or commit them — inject via CI secret store / runtime env.
