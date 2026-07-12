# DevOps & Infrastructure Reference

## Core Principles
- **IaC**: infra as version-controlled code (Terraform, Pulumi, CloudFormation, Ansible). Declarative desired-state, not imperative scripts. `plan` before `apply`; store **state** remotely + locked (S3+DynamoDB, TF Cloud) — never local/committed. Modules for reuse; `import` existing resources rather than click-ops.
- **Immutable infra**: never patch running servers; bake a new image/artifact and replace. Kills config drift + **snowflake servers** (hand-tuned, unreproducible). Reproducible builds via pinned versions + lockfiles.
- **Idempotency**: re-running a deploy/config converges to same state (Ansible, k8s reconcile). No "run once" side effects.
- **Config vs code**: 12-factor — config (URLs, creds, flags) from **env/secret store**, not baked in. Same artifact promotes dev→staging→prod; only env differs.

## CI/CD Pipelines
- Stages: lint → unit → build artifact → integration → deploy staging → smoke → deploy prod. Fail fast: cheap checks first.
- **CI** = merge + test every commit on shared main. **CD** = auto-deliver every green build (delivery = ready to ship; deployment = auto to prod).
- Cache deps keyed on lockfile hash (`~/.cache/pip`, `node_modules`, `.m2`). Build artifact **once**, promote same bytes across envs — never rebuild per env (drift risk).
- Gates: required checks, branch protection, manual approval for prod. Ephemeral runners (clean each build). Pipeline-as-code lives in repo (`.github/workflows`, `.gitlab-ci.yml`).

## Deploy Strategies & Rollback
- **Blue-green**: two identical envs; deploy to idle (green), smoke-test, flip router. Instant rollback = flip back. Costs 2x infra.
- **Canary**: route small % (1→5→25→100) to new version, watch metrics/error rate, auto-rollback on SLO breach. Needs good observability.
- **Rolling**: replace instances batch by batch (k8s default `maxSurge`/`maxUnavailable`). No extra env but mixed versions in flight.
- **Feature flags**: decouple deploy from release; dark-launch, kill-switch without redeploy (LaunchDarkly, Unleash).
- **Rollback plan mandatory**: DB migrations must be backward-compatible (expand-contract: add col → dual-write → backfill → switch → drop later) so old + new code coexist. Never a migration that only the new code survives.

## Containers & Orchestration
- Image = immutable filesystem + metadata; container = running instance. Registry stores tagged images (ECR, GHCR, Docker Hub). Pin digests/tags, never rebuild-on-`:latest` in prod.
- **Dockerfile**: `FROM python:3.12-slim` (pinned, not `:latest`). Layer order = cache: copy dep manifest → install → **then** copy source, so code edits don't bust the dep layer.
  ```
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  ```
- Multi-stage: build in fat image, `COPY --from=build /app/bin` into slim runtime → ships no toolchain. Run non-root: `RUN useradd app && USER app`. `.dockerignore` `.git`/`node_modules` (smaller context, no secret leak). **Never** secrets in `ARG`/`ENV` — persist in layers; use build secrets / runtime mounts.
- **Kubernetes**: Pod (smallest unit) → Deployment (replicas + rollout) → Service (stable VIP) → Ingress (L7 route/TLS). ConfigMap/Secret for config. Liveness probe (restart if hung) vs readiness (pull from LB until ready). `requests` (scheduling) vs `limits` (cap; mem over-limit = OOMKill). HPA autoscales on metrics.

## Observability
- **Three pillars**: **logs** (discrete events, structured JSON), **metrics** (numeric time-series, cheap aggregates — Prometheus), **traces** (request path across services — OpenTelemetry, Jaeger). Correlate via trace/request ID.
- **RED** (services): Rate, Errors, Duration. **USE** (resources): Utilization, Saturation, Errors. Alert on **symptoms/SLOs** (user-facing) not causes; page only on actionable.
- SLI (measured) → SLO (target, e.g. 99.9%) → error budget (1−SLO) governs release pace. Dashboards (Grafana) + alerting (Alertmanager, PagerDuty).

## Secrets, Config, GitOps
- Secrets in a manager (Vault, AWS Secrets Manager, SOPS, Sealed Secrets), injected at runtime, **short-lived + rotated**. Never in code/images/logs/env-committed. If leaked → rotate immediately (git history keeps it).
- **GitOps**: git is single source of truth for infra + app state; agent (Argo CD, Flux) continuously reconciles cluster to repo. Deploy = merge PR; rollback = revert commit. Full audit trail.
- Config mgmt (Ansible/Chef/Puppet) for mutable fleets; prefer immutable images where possible.

## Environments, Artifacts, Registries
- Promote **one immutable artifact** dev→staging→prod; only injected config/secrets differ. Staging mirrors prod (same infra shape, scaled down). Prod-parity avoids "works in staging" surprises.
- Artifact registry versions built outputs (container images, jars, wheels, npm) with immutable tags/digests + provenance/SBOM. Retention/GC policies prune old images. Sign artifacts (cosign) + verify at deploy for supply-chain integrity.
- Ephemeral preview envs per PR (spin-up on open, tear-down on merge) catch integration issues early.

## Terraform / IaC Workflow
- `init` (backend+providers) → `plan` (diff, review in PR) → `apply` (gated) → `state`. Lock providers (`.terraform.lock.hcl`) + pin module versions. `terraform fmt`/`validate` in CI; `plan` on PR, `apply` on merge.
- Separate state per env/component (blast-radius). Never edit cloud resources by hand (drift); `import` instead. Secrets never in `.tf`/state plaintext — reference a secret store.

## DORA Metrics & On-Call
- **Four keys**: deploy frequency, lead time (commit→prod), change failure rate, MTTR (mean time to restore). Elite = deploy on-demand, lead time <1h, CFR <15%, MTTR <1h. Fifth (reliability): meeting SLOs. Optimize all four together — speed without stability (high CFR) is false progress.
- On-call: actionable alerts only (no noise/fatigue), runbooks per alert, clear escalation ladder, blameless postmortems (systems not people), track + budget toil. Rotations sized for sustainable load; follow-the-sun for global teams. Incident roles: commander, comms, ops.

## Gotchas → Fix
- **Snowflake servers** (hand-configured, irreproducible) → codify in IaC, rebuild from scratch to verify; treat servers as cattle not pets.
- **Config drift** (running ≠ declared) → periodic reconcile / GitOps auto-sync; detect with `terraform plan` in CI (nonzero diff = drift).
- **No rollback plan** → require backward-compatible migrations + blue-green/canary before shipping; test the rollback, not just the deploy.
- **Manual deploys** ("works on my machine", missed steps) → automate in pipeline; forbid hand-`ssh` prod changes.
- **Secrets in code/git** → move to secret store, scan repo (`gitleaks`, `trufflehog`), rotate anything committed — history is forever.
- **No monitoring** → can't tell if deploy broke prod; add health checks + RED metrics + alerting before scaling.
- **`:latest` tag** → non-reproducible pulls, silent version skew; pin tags/digests.
- **Local/committed TF state** → corruption + secret leak; use remote locked backend.
- **Stale image after change** → compose `restart` reuses old image; `up --build` to recreate. Code-mount edit needs process restart; dep/Dockerfile edit needs rebuild.
- **Retry storms / no backoff** → cascading failure; add exponential backoff + jitter + circuit breakers + timeouts (never unbounded).
- **Migration that only new code survives** → deploy/rollback race breaks prod; always expand-contract.
- **Alert fatigue** → tune to symptoms/SLO burn, delete flapping alerts, page only actionable.

## Shell (deploy scripts)
- Start with `set -euo pipefail` (exit on error, unset var, pipe failure). Quote expansions `"$var"` `"$@"`. Cleanup `trap 'rm -f "$tmp"' EXIT`. `cmd || true` only where failure is genuinely fine.
