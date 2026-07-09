# Release Management
## Semantic Versioning (SemVer)
- `MAJOR.MINOR.PATCH` — MAJOR = breaking API change, MINOR = backward-compatible feature, PATCH = backward-compatible bug fix.
```
1.4.2 -> 1.4.3 (bugfix) -> 1.5.0 (feature) -> 2.0.0 (breaking)
1.0.0-rc.1+build.42   (pre-release: -rc.1 | metadata: +build.42)
```
- Pre-release tags (`-alpha`, `-beta`, `-rc.1`) sort below the release. `0.y.z` = unstable/anything-may-change. Precedence ignores build metadata.

## Branching strategies
- Trunk-based: everyone commits to `main` (trunk) daily; very short-lived branches; feature flags hide unfinished work; requires strong CI. Best for CI/CD + high throughput.
- GitHub Flow: `main` always deployable; short feature branches -> PR -> merge -> deploy. Simple, continuous-deploy friendly.
- GitFlow: long-lived `main` + `develop`, plus `feature/*`, `release/*`, `hotfix/*`. Structured, good for versioned/scheduled releases; heavier, slower, merge-conflict prone. Overkill for continuous deployment.
```
GitFlow: feature/* -> develop -> release/* -> main (tag) ; hotfix/* -> main + develop
```

## Release cadence / trains
- Release train: fixed schedule (e.g. every 2 wk); features board the next train if ready, else wait for the following one — date is fixed, scope flexes. Decouples release from feature completion, reduces coordination.
- Cadence choices: continuous deployment (every merge), scheduled trains, or milestone/big-bang.

## Feature flags / toggles
- Decouple deploy from release: ship code dark, enable at runtime. Types: release toggles (short-lived, hide WIP), experiment (A/B), ops (kill switch), permission (entitlement).
- Enables trunk-based dev, canary rollout, instant kill without redeploy. Risk: flag debt — remove stale release flags promptly.

## Release strategies (exposure)
- Big-bang: everything to everyone at once — high blast radius; reserve for forced cutovers or tightly-coupled changes.
- Incremental / phased: roll out by cohort/region/percentage, learning between phases; contains risk.
- Dark launch: deploy code to prod but keep it off (flag off / no UI); exercise it against real load/traffic (often shadowed) to validate infra + performance before exposing.
- Progressive delivery: canary + automated analysis + gradual ramp; expose to more users only as metrics stay healthy.

## Deployment strategies (mechanics)
- Blue-green: two identical envs; switch router blue<->green; instant rollback by switching back. Cost: double infra.
- Canary: route small % of traffic to new version, watch metrics, ramp up or roll back. Ramp e.g. 1% -> 5% -> 25% -> 100%, with a bake time per stage.
- Rolling: replace instances in batches; no double infra, but mixed versions live simultaneously (needs backward-compatible contracts).
- Recreate: stop old, start new (downtime). Shadow: mirror traffic to new version without serving its responses.

## Canary analysis
- Automated canary analysis (ACA): compare canary vs a same-age baseline (control), not the old fleet, on golden signals (latency, error rate, saturation, traffic) with statistical thresholds; auto-halt/roll back on regression.
- Same-age baseline cancels out load/time-of-day effects. Define pass/fail + bake time per stage; alert on guardrail-metric breach.

## Rollback vs roll-forward + hotfix
- Rollback: revert to last-known-good (redeploy prior artifact, switch blue-green, disable flag, or DB-safe down-migration). Design migrations backward-compatible (expand/contract) so rollback is safe.
- Roll-forward (fix-forward): ship a new corrective patch instead of reverting — preferred when a destructive migration already ran forward or when reverting is riskier/slower than fixing. Choose by which restores service fastest + safest; keep both playbooks ready.
- Hotfix: urgent patch off the production tag -> test -> deploy -> merge back to main/develop so the fix isn't lost.

## API versioning + compatibility
- Version APIs (URI `/v2`, header, or media type). Additive changes only within a version; a breaking change means a new version.
- Deprecation: announce, emit a `Sunset` header + timeline, dual-run old + new, monitor usage, then retire. Consumer-driven contract tests catch accidental breaks pre-release.

## Changelog + release notes
- Changelog for humans (Keep a Changelog buckets: Added / Changed / Deprecated / Removed / Fixed / Security). Auto-generate from Conventional Commits (`feat`/`fix`/`BREAKING CHANGE` drive the SemVer bump).
- Release notes = user-facing highlights + upgrade/migration steps + known issues; distinct from an internal commit log.

## Multi-service release coordination
- Default to independent deployability; services that MUST ship together are a distributed monolith — fix the coupling.
- When unavoidable: keep contracts backward + forward compatible so any deploy order is safe; expand/contract across service boundaries; flip a feature flag to activate only after all services are up. Avoid lockstep deploys.

## Incident / rollback runbook
- Detect (SLO breach) -> declare + assign an incident commander -> decide rollback vs fix-forward -> restore known-good -> verify (smoke + metrics) -> comms (status page/stakeholders) -> blameless post-mortem + actions.
- Pre-write + rehearse (game days). Define an automatic rollback trigger (e.g. error rate > X% for N min).

## Compliance / approval gates
- Segregation of duties: author != approver != deployer; every change carries a ticket + audit trail. SOX/SOC2/PCI may require documented approvals, evidence, and commit->deploy traceability.
- Automate evidence capture in the pipeline (who/what/when/approval). Risk-based gating: pre-approve standard/low-risk changes; reserve heavy review for high-risk. Emergency-change path still records + retro-reviews.

## Versioning artifacts + tagging
- Tag every release in VCS (`v2.3.0`), immutable. Artifacts named by version + build (e.g. `app-2.3.0+build.417`). Lock dependency versions (lockfiles) for reproducible builds. Calendar versioning (CalVer, `YYYY.MM`) is an alternative when time, not API compatibility, is the meaningful axis.

## Environments
- dev -> test/CI -> staging (prod-like, final validation) -> production. Optionally UAT/pre-prod. Keep staging config + data shape close to prod; promote the same built artifact through envs (build once, deploy many).

## Change management
- Change request -> review/approval (CAB for high-risk) -> scheduled window -> execute -> verify -> record. Classes: standard (pre-approved), normal, emergency. Maintain a changelog + release notes; tag the release in VCS.

## CI/CD pipeline
- Stages: commit -> build (once, immutable artifact) -> unit tests -> integration tests -> security/lint/SAST scan -> deploy to staging -> smoke/e2e -> promote to prod (manual gate = continuous delivery; auto = continuous deployment). Artifact promoted unchanged across envs; config injected per env (12-factor).

## Database migrations
- Expand/contract (parallel change): (1) add new schema additively, (2) dual-write/backfill, (3) switch reads, (4) drop old — each step deployable + reversible. Never couple a destructive migration to the app deploy that needs both old + new code alive during rollout.

## Release checklist
- Version bumped + tagged; changelog/release notes written; CI green (tests, lint, security scan); migrations reviewed + reversible; feature flags configured; rollback plan documented; monitoring/alerts + dashboards ready; stakeholders + support notified; deploy window scheduled; post-deploy smoke tests defined; on-call assigned.

## Pitfalls -> Fix
- **Deploy == release conflation**: can't ship code without exposing features. Fix: decouple via feature flags; deploy dark, release by toggle.
- **Long-lived feature branches**: merge hell + integration risk. Fix: trunk-based + short branches + flags; integrate daily.
- **No rollback plan / irreversible migrations**: a bad release is stuck forward-only. Fix: backward-compatible expand/contract migrations; rehearse rollback; keep prior artifact deployable.
- **Manual, snowflake deploys**: unrepeatable, error-prone. Fix: automate the pipeline; build once, promote the same artifact; infra-as-code.
- **Version bumps by feel (breaking change as PATCH)**: consumers break unexpectedly. Fix: follow SemVer strictly; automate from conventional commits.
- **Big-bang releases**: large blast radius, hard to diagnose. Fix: small frequent releases; canary/rolling to limit exposure.
- **Feature-flag debt**: stale flags create dead paths + combinatorial risk. Fix: track flags with owners + expiry; remove after full rollout.
- **Staging diverges from prod**: "works in staging" then fails in prod. Fix: parity in config/data-shape/infra; same artifact promoted.
- **Hotfix not merged back**: fix reappears as a regression next release. Fix: always merge hotfix into mainline + develop.
- **No post-deploy verification**: broken release discovered by users. Fix: automated smoke tests + monitoring + defined rollback trigger (error-rate SLO).
- **Skipping CAB/change record for "urgent" fixes**: no audit trail, repeat incidents. Fix: emergency-change path that still records + reviews after the fact.
- **Lockstep deploys across services**: one lagging service blocks all; rollback is all-or-nothing. Fix: backward/forward-compatible contracts; deploy independently in any order; activate via flag.
- **Rolling back after an irreversible forward migration**: data loss/corruption. Fix: expand/contract; once a destructive step ran, prefer fix-forward; back up before.
- **Breaking a live API without a new version**: silent consumer outages. Fix: version + additive-only changes; deprecation window with `Sunset` header + contract tests.
- **Undocumented release / no changelog**: users + support blindsided. Fix: auto-generate changelog from commits; publish user-facing notes with upgrade steps.
- **Rubber-stamp CAB / approval theater**: slows delivery without cutting risk. Fix: risk-based gating; pre-approve standard changes; automate evidence for low-risk.
- **Canary judged against the old fleet**: load/time skew hides regressions. Fix: compare against a same-age baseline on golden signals with statistical thresholds.
