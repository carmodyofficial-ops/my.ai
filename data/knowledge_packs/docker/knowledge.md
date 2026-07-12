# Docker Reference

## Images vs Containers
- **Image**: read-only stack of layers + JSON config (env, entrypoint, cmd). **Container**: image + a thin writable layer + runtime namespaces/cgroups.
- `docker build -t app:1.0 .` -> image; `docker run app:1.0` -> container. N containers per image; writable layer is discarded on `rm` unless data is on a volume.
- Identity: images are content-addressed by digest (`sha256:...`); tags are mutable pointers. Reference by digest for immutability.
- Inspect: `docker history img` (layers+sizes), `docker inspect`, `docker image ls`, `docker system df` (disk), `docker system prune -a` (reclaim).

## Dockerfile Instructions
- `FROM node:20-slim` — base; pin a tag/digest; starts each stage.
- `RUN a && b` — executes at build, one layer; chain with `&&` and clean in the *same* layer (`rm -rf /var/lib/apt/lists/*`) or the cruft stays in a lower layer forever.
- `COPY src/ /app/` — copy from build context; deterministic. Prefer over `ADD`.
- `ADD` — COPY + auto-untar local archives + fetch URLs. Use ONLY for those; else COPY.
- `WORKDIR /app` — sets/creates cwd; use instead of `RUN cd` (which doesn't persist).
- `ENV K=v` — runtime env, baked into image. `ARG X` — build-time only (`--build-arg`), not in final image, but visible in `docker history` — never a secret.
- `EXPOSE 8080` — metadata only; does NOT publish (need `-p`).
- `USER node` — drop from root; put after installs that need root.
- `CMD ["node","app.js"]` — default argv, overridable at `docker run`.
- `ENTRYPOINT ["node"]` — fixed executable; CMD supplies its default args. Use **exec/JSON form** — shell form (`CMD node app.js`) wraps in `/bin/sh -c`, so your process is PID != 1 and **doesn't receive SIGTERM** (slow/failed graceful shutdown).

## Layer Caching
- Each instruction = a cached layer keyed on the instruction + inputs; change one and **all subsequent layers rebuild**.
- Order **least -> most volatile**. Install deps before copying source:
```dockerfile
COPY package*.json ./
RUN npm ci
COPY . .          # source churns; deps layer stays cached
```
- `COPY . .` before install busts the cache on every code edit. Pin dep versions for reproducible cache. `--no-cache` forces full rebuild.

## Multi-stage Builds
```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o app

FROM gcr.io/distroless/static:nonroot
COPY --from=build /src/app /app
USER nonroot
ENTRYPOINT ["/app"]
```
- Heavy toolchain/build-secrets stay in the build stage; only the artifact lands in the runtime image. Shrinks size, drops attack surface. `--target build` builds a specific stage; `COPY --from=nginx:alpine ...` copies from any image.

## Image Size
- Small base: `-slim`, `alpine` (musl — watch glibc/DNS quirks), or **distroless** (no shell/package manager — great security, but no `exec sh` to debug; use `:debug` variant).
- Combine RUN layers, clean package caches in-layer, `.dockerignore` the context, multi-stage. `docker history --no-trunc` finds the fat layer.

## .dockerignore
- Excludes paths from the build context sent to the daemon: `node_modules`, `.git`, `.env`, `dist`, `**/*.log`. Speeds builds, prevents secret/cruft leakage into layers.

## Volumes vs Bind Mounts
- **Named volume** (`-v pgdata:/var/lib/postgresql/data`): Docker-managed, survives `rm`, portable, correct perms — use for DB/stateful data.
- **Bind mount** (`-v $(pwd):/app` or `--mount type=bind,...`): host path -> container; dev source/hot-reload; tied to host layout; can shadow image files.
- **tmpfs** (`--tmpfs /tmp`): RAM-only, for secrets/scratch.
- Anonymous volumes: a `VOLUME` in a Dockerfile or unnamed `-v` creates untracked volumes that accumulate; `docker volume prune`.

## docker run Flags
- `-p 8080:80` publish host:container. `-P` all EXPOSEd to random ports.
- `-v name:/data` volume · `-v $(pwd):/app` bind · `--mount type=...,src=,dst=,ro` (explicit, fails loudly on missing source unlike `-v`).
- `-e K=v` / `--env-file .env`. `--rm` auto-remove. `-d` detached. `--name web`.
- `--network mynet`. `--restart unless-stopped`. `--read-only` (immutable rootfs).
- Resource limits: `--memory 512m` (exceed -> **OOMKilled 137**), `--cpus 1.5`, `--pids-limit`. Without limits a container can starve the host.

## Networks
- Default `bridge` (no name-based DNS between containers). Create a user network: `docker network create app` — then containers resolve each other by **container/service name** via embedded DNS.
- `host` (no isolation, shares host net), `none`, `overlay` (multi-host/swarm), `macvlan`.
- Published ports (`-p`) are reachable from the host; unpublished are internal to the network.

## docker compose
```yaml
services:
  web:
    build: .
    ports: ["8080:80"]
    environment: { NODE_ENV: production }
    depends_on:
      db: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 10s
      timeout: 3s
      retries: 3
  db:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]
volumes: { pgdata: }
```
- `docker compose up -d` / `down` / `logs -f` / `ps`. All services share an implicit network; reach each other by service name (`db:5432`).
- Plain `depends_on: [db]` = **start order only, not readiness**; use `condition: service_healthy` with a healthcheck.

## Healthchecks
- `HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -f http://localhost/health || exit 1`. States: starting -> healthy/unhealthy. Doesn't restart alone; orchestrators/compose act on it.

## BuildKit
- Default builder (`DOCKER_BUILDKIT=1`). Parallel stages, better cache, secrets, cache mounts.
- Build secrets (never in a layer): `RUN --mount=type=secret,id=npm cat /run/secrets/npm` + `docker build --secret id=npm,src=.npmrc`.
- Cache mount: `RUN --mount=type=cache,target=/root/.cache go build`. Multi-arch: `docker buildx build --platform linux/amd64,linux/arm64 --push`.

## Registries
- `docker login`, `docker tag app:1.0 ghcr.io/org/app:1.0`, `docker push`. Digest pin: `image@sha256:...`.

## Gotchas -> Fix
- **Cache busted every build**: `COPY . .` before deps -> copy manifest + install first, source last.
- **`:latest` non-reproducible / no rollback**: pin tags or digests.
- **Huge image**: build tools in final layer -> multi-stage; clean apt caches in-layer; slim/distroless base.
- **Secrets in layers**: baked via `ENV`/`ARG`/`COPY` are recoverable with `docker history`/`docker save` -> BuildKit `--secret`, runtime env, add to `.dockerignore`.
- **PID 1 / zombie reaping / signals ignored**: shell-form CMD or an app that doesn't reap children -> use exec form; add `--init` (or `tini`) for a proper init.
- **SIGTERM ignored -> slow shutdown/10s kill**: ensure the app is PID 1 (exec form) and handles SIGTERM.
- **Volume perms denied**: container non-root UID can't write a host bind dir -> match UID (`--user`), `chown` in build, or use a named volume.
- **Data loss on `rm`**: writable layer is ephemeral -> named volume for stateful dirs.
- **Anonymous volumes piling up**: `docker volume prune`; avoid stray `VOLUME`/unnamed `-v`.
- **Alpine DNS/musl breakage**: native modules or getaddrinfo differ -> use `-slim` (glibc) if bitten.
- **`ADD` surprises**: auto-untar/URL fetch -> use COPY unless you need those.
- **Build context too big/slow**: huge `.git`/`node_modules` sent to daemon -> `.dockerignore`.
- **OOMKilled (exit 137)**: hit memory limit -> raise `--memory` or fix leak; check `docker inspect --format '{{.State.OOMKilled}}'`.
- **Port not reachable**: `EXPOSE` alone doesn't publish -> add `-p`.
