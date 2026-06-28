# Docker Reference

## Images vs Containers
- **Image**: read-only template (layers). **Container**: running instance of an image (writable layer on top).
- `docker build -t app:1.0 .` -> image. `docker run app:1.0` -> container. Many containers per image.

## Dockerfile Instructions
- `FROM node:20-slim` — base image; pin a version, start each stage.
- `RUN apt-get update && apt-get install -y x` — execute at build, creates a layer. Chain with `&&` to reduce layers.
- `COPY src/ /app/` — copy build-context files. Prefer over `ADD`.
- `ADD` — like COPY but also untars archives and fetches URLs. Use **only** for those; else COPY.
- `WORKDIR /app` — sets cwd (creates dir); use instead of `RUN cd`.
- `ENV NODE_ENV=production` — runtime env var, persists in image.
- `ARG VERSION=1` — build-time only var (`--build-arg`); not in final image. Don't use for secrets.
- `EXPOSE 8080` — documents port; does NOT publish (need `-p`).
- `CMD ["node","app.js"]` — default args/command, overridable at `docker run`.
- `ENTRYPOINT ["node"]` — fixed executable; CMD supplies default args. Use exec (JSON) form for proper signals.

## Layer Caching
- Each instruction = cached layer; invalidated when its inputs change, busting all later layers.
- Order **least->most changing**. Copy manifest + install deps **before** copying source:
```dockerfile
COPY package*.json ./
RUN npm ci
COPY . .
```
- Pin dep versions for reproducible cache.

## Multi-stage Builds
```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN go build -o app

FROM gcr.io/distroless/base
COPY --from=build /src/app /app
ENTRYPOINT ["/app"]
```
- Build heavy deps in one stage; copy only artifacts into a slim runtime. Shrinks image, drops toolchain/secrets.

## .dockerignore
- Excludes paths from build context: `node_modules`, `.git`, `.env`, `dist`. Speeds builds, avoids leaking secrets.

## docker run Flags
- `-p 8080:80` host:container port publish.
- `-v name:/data` or `--mount type=volume,src=name,dst=/data` volume.
- `-v $(pwd):/app` bind mount (dev hot-reload).
- `-e KEY=val` env var. `--env-file .env`.
- `--rm` remove on exit. `-d` detached. `--name web` name it.
- `--network mynet` attach network.

## Volumes vs Bind Mounts
- **Named volume**: Docker-managed, persists data (DBs); survives container removal.
- **Bind mount**: host path -> container; for dev source/config. Tied to host layout.
- Container writable layer is ephemeral — **data lost without a volume**.

## docker compose
```yaml
services:
  web:
    build: .
    ports: ["8080:80"]
    environment: { NODE_ENV: production }
    depends_on: [db]
    networks: [app]
  db:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]
    networks: [app]
volumes: { pgdata: }
networks: { app: }
```
- `docker compose up -d` / `down`. `depends_on` = start order, not readiness.

## Networking
- Default `bridge`; published ports reach host.
- In compose, services join a user network and resolve each other by **service name** DNS (`db:5432`).

## Best Practices
- Small base (`-slim`/`alpine`/distroless). Multi-stage to shrink.
- `USER node` — run non-root.
- Pin versions, never rely on `:latest`.
- One process per container.
- Inject secrets at runtime (env/`--mount type=secret`), never bake into layers.

## Gotchas -> Fix
- **Cache busted**: copying source before installing deps -> copy manifest+install first.
- **`:latest` non-reproducible**: pin tags/digests.
- **Root user**: add `USER`.
- **Secrets in layers**: visible via `docker history`; use build secrets/runtime env, add to `.dockerignore`.
- **ADD vs COPY**: use COPY unless untar/URL needed.
- **CMD vs ENTRYPOINT**: ENTRYPOINT = fixed binary, CMD = default args; combine them.
- **Data loss**: mount a named volume for stateful dirs.
