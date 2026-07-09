# CI/CD Pipelines

## CI vs CD vs Continuous Deployment
- Continuous Integration (CI): every push merges to mainline frequently (≥ daily) and triggers automated build + test on a shared branch. Goal: catch integration breakage in minutes, keep `main` always green. Trunk-based dev + short-lived branches beat long-lived feature branches.
- Continuous Delivery (CD): every green build is automatically packaged into a deployable artifact and can be released to prod at any time by a button press. Deploy is a business decision, not a technical scramble.
- Continuous Deployment: every green build that passes all gates auto-deploys to prod with no human step. Requires high test confidence, progressive delivery, fast rollback.
- Progression: CI → Continuous Delivery (manual prod approval) → Continuous Deployment (fully automatic).

## Pipeline stages (typical order)
1. Build/compile — produce binaries; fail fast on compile errors.
2. Unit tests + lint/format + type check — fastest, run first, parallel.
3. Static analysis / security scan (SAST, SCA, secret scan) — fail on high severity.
4. Integration/component tests — with real-ish deps (Testcontainers).
5. Package — build immutable artifact (container image, jar, wheel) tagged with commit SHA.
6. Publish artifact to registry (immutable, signed).
7. Deploy to staging → smoke/E2E/contract tests → deploy to prod (progressive).
8. Post-deploy verification — health checks, synthetic monitors, SLO watch.
- Order by cost + signal: cheap/high-signal gates first so 90% of failures surface in <2 min.

## Fast feedback
- Target: CI feedback < 10 min (ideal), PR merge pipeline < 15 min. Slow pipelines kill trunk-based flow and encourage batching.
- Parallelize: shard test suites across runners; run independent stages concurrently (matrix builds).
- Caching: cache dependencies (`~/.m2`, `node_modules`, `~/.cargo`, pip wheels) keyed on lockfile hash; layer-cache Docker builds (order Dockerfile least→most volatile; use BuildKit `--mount=type=cache`); cache compiled artifacts (ccache, Gradle build cache, Bazel/Nx remote cache).
- Fail fast: `--fail-fast`/`-x` on the first broken gate; run changed-scope tests first (test impact analysis, `nx affected`).
- Split fast PR pipeline (lint+unit+build) from slow nightly (full E2E, load, security deep scan).

## Artifacts + immutability
- Build once, promote the same artifact through every environment. Never rebuild per environment — rebuilding changes inputs and invalidates prior test results.
- Immutable + content-addressable: tag images with git SHA (and semver), never mutate `latest` in prod. Digest-pin (`image@sha256:...`) for prod.
- Config is injected at deploy (env vars / secrets / config maps), NOT baked per-env into the artifact. Same binary, different config = twelve-factor.
- Sign artifacts (Cosign/Sigstore) + generate SBOM (Syft) + provenance (SLSA) for supply-chain integrity.

## Environments + promotion
- Ladder: dev → CI/test → staging (prod-like) → prod. Promotion = deploy the already-tested artifact + run env-specific gates.
- Staging should mirror prod (same infra shape, data-shaped fixtures). Ephemeral preview environments per PR for review.
- Gate promotion on test results + approvals; record what artifact SHA is in each env (deployment ledger).

## Deployment strategies
- Rolling: replace instances in batches (maxSurge/maxUnavailable). Cheap, no extra capacity; slow rollback, mixed versions during roll.
- Blue-green: two full envs; deploy to idle (green), smoke test, flip router/LB to green; instant rollback = flip back. Costs 2× capacity; watch DB schema compatibility.
- Canary: route small % (1→5→25→100) to new version; compare error rate/latency/SLO vs baseline; auto-promote or auto-rollback. Needs good metrics + traffic. Tools: Argo Rollouts, Flagger, Spinnaker.
- Feature flags: decouple deploy from release; ship code dark, enable per cohort, kill-switch instantly, run A/B. Tools: LaunchDarkly, Unleash, Flagsmith. Prune stale flags (they accrue tech debt).
- Shadow/dark traffic: mirror prod traffic to new version, discard responses, compare — zero user risk.

## Automated testing gates
- Test pyramid: many fast unit, fewer integration, few E2E. Inverted pyramid (mostly E2E) = slow + flaky.
- Gate on: compile, unit/integration pass, coverage threshold (as a floor, not a target to game), contract tests (Pact) for service boundaries, smoke tests post-deploy.
- Quarantine flaky tests (don't let them block); track + fix or delete — a flaky gate that people re-run trains everyone to ignore red.

## Security scanning
- SAST: static analysis of source for vulns (Semgrep, CodeQL, SonarQube). Early, no running app; some false positives.
- DAST: attacks the running app (OWASP ZAP, Burp). Finds runtime/config issues; needs a deployed target.
- SCA: scans dependencies/CVEs + licenses (Dependabot, Renovate, Snyk, Trivy, Grype). Most real-world breaches are known CVEs in deps.
- Secret scanning: block committed credentials (gitleaks, trufflehog, GitHub secret scanning, pre-commit hooks).
- IaC/container scanning: Trivy, Checkov, tfsec. Fail build on high/critical; allow risk-accepted exceptions with expiry.

## Rollback + versioning
- Rollback must be one command / one click and faster than roll-forward. Blue-green flip or `kubectl rollout undo` / redeploy previous SHA.
- Semver artifacts; keep last N releases available in registry. DB migrations must be backward-compatible (expand/contract): deploy schema change first, decoupled from code, so old + new code both work → enables rollback.
- Prefer roll-forward for data-affecting changes; rollback for stateless app bugs.

## GitOps + pipeline as code
- GitOps: git is the single source of truth for declarative infra + app state; an agent (Argo CD, Flux) continuously reconciles cluster to match git; drift is auto-corrected. Deploy = merge PR; rollback = git revert. Full audit trail.
- Pipeline as code: pipeline lives in repo (`.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`), versioned + reviewed + reusable (composite actions, templates). No click-configured pipelines.

## Secrets in pipelines
- Never hardcode/commit secrets or echo them in logs (mask). Inject from a manager (Vault, AWS/GCP Secrets Manager, GitHub OIDC → short-lived cloud creds, not static keys).
- Prefer OIDC federation over long-lived cloud access keys. Scope least privilege per pipeline; rotate; audit access.
- Beware secret exfil via malicious PR from forks — don't expose prod secrets to `pull_request` from forks; use `pull_request_target` carefully.
- Pin third-party CI actions/plugins to a commit SHA (not a mutable tag) — a hijacked `@v3` tag runs arbitrary code with your secrets. Review dependency updates.

## Pipeline health metrics
- Track: pipeline duration (p50/p95), success rate, mean time to recovery of a red `main`, flaky-test rate, queue/wait time for runners.
- Keep `main` green: block merge on required checks; auto-revert or roll forward fast when `main` breaks — a red mainline blocks the whole team.
- Merge queues (GitHub merge queue, Bors) test the post-merge combination to prevent "semantic merge conflicts" where two individually-green PRs break together.
- Right-size runners + autoscale; cache warmers for cold caches; ephemeral, clean runners each run for reproducibility.

## Gotchas -> Fix
- Flaky tests block merges, people mass re-run -> quarantine + track flakies, fix root cause (timing/order/shared state), enforce determinism; never "re-run until green".
- Pipeline too slow (>30 min), devs batch changes -> parallelize/shard, cache deps+layers, split fast-PR vs nightly, test-impact analysis.
- Non-reproducible builds ("works on my machine") -> pin exact dep versions (lockfiles), hermetic/containerized builds, pin base image digests, no network at build time beyond locked deps.
- Rebuilding artifact per environment -> build once, promote same SHA; inject config at deploy.
- Manual approval/deploy gates everywhere -> automate low-risk paths, reserve approvals for prod/high-risk; measure lead time.
- Secrets leaked in logs or committed -> mask outputs, secret-scan in CI + pre-commit, inject from Vault/OIDC, rotate on exposure, block fork PR secret access.
- Mutating `latest` in prod -> immutable SHA/semver tags, digest-pin prod, keep N prior versions for rollback.
- Rollback broken by non-backward-compatible DB migration -> expand/contract migrations, decouple schema from code deploy, test rollback path.
- Canary with no metrics comparison -> instrument RED/SLO, auto-rollback on regression via Argo Rollouts/Flagger; else canary is just a slow full deploy.
- Coverage gate gamed by useless tests -> treat coverage as a floor + review test quality (mutation testing, PR review), gate on behavior not %.
- Inverted test pyramid (all E2E) -> slow, flaky; push logic down to unit/integration, keep E2E for critical journeys.
- SCA/SAST ignored due to false-positive noise -> tune rules, fail only on high/critical + reachable, allow expiring risk-accepted exceptions.
- Deploy != release coupling forces risky big-bang launches -> feature-flag dark ships, decouple, roll out per cohort with kill-switch.
- Pipeline config click-built in UI, not versioned -> move to pipeline-as-code in repo, reviewed + reusable templates.
