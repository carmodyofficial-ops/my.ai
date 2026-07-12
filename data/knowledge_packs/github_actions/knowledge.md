# GitHub Actions CI/CD Reference

## File Location & structure
- Workflows live in `.github/workflows/*.yml` (one file = one workflow). Top-level keys: `name`, `on`, `permissions`, `concurrency`, `env`, `jobs`.
- Hierarchy: workflow -> jobs (parallel, each on a fresh VM) -> steps (sequential in a job). Steps in a job share a filesystem/workspace; jobs do NOT (pass data via artifacts/outputs).

## Triggers (`on:`)
```yaml
on:
  push: { branches: [main], paths: ['src/**'], tags: ['v*'] }
  pull_request: { branches: [main], types: [opened, synchronize, reopened] }
  schedule: [{ cron: '0 6 * * 1' }]     # UTC, min granularity 5m, no guaranteed on-time
  workflow_dispatch:                     # manual run + inputs
    inputs: { env: { type: choice, options: [staging, prod] } }
  workflow_call:                         # reusable workflow
```
- `paths`/`branches`/`tags` (+ `-ignore` variants) filter runs. Scheduled/dispatch runs use the **default branch's** workflow file.

## Jobs
- Parallel by default; serialize + gate with `needs: [build]` (a job's `if` still evaluates on failure — guard with `if: success()`/`always()`).
- `runs-on: ubuntu-latest` (or `windows-latest`, `macos-latest`, self-hosted via labels `[self-hosted, linux, x64]`).
- Cross-job data: `outputs:` from a step (`echo "k=v" >> "$GITHUB_OUTPUT"`) surfaced as `jobs.<id>.outputs`, consumed via `needs.build.outputs.k`.

## Steps & actions
- `uses:` runs a published action; `run:` runs shell (`shell: bash` default on Linux). `with:` passes inputs; `env:` sets vars.
- **Pin third-party actions to a full commit SHA** (tags/branches are mutable = supply-chain risk); first-party `actions/*` by major tag is common but SHA is safest.
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4
    with: { node-version: 20, cache: npm }
  - run: npm ci && npm test
```

## Matrix
```yaml
strategy:
  fail-fast: false
  max-parallel: 4
  matrix:
    node: [18, 20, 22]
    os: [ubuntu-latest, windows-latest]
    include: [{ node: 20, os: ubuntu-latest, coverage: true }]
    exclude: [{ node: 18, os: windows-latest }]
runs-on: ${{ matrix.os }}
```
- Combinations multiply (3×2=6 jobs). `fail-fast: false` keeps others running after one fails. `include` adds/augments, `exclude` trims.

## Caching (`actions/cache`)
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: npm-${{ runner.os }}-
```
- Exact `key` hit = full restore, no save. Miss -> `restore-keys` prefix (partial) then save new key at job end (immutable — a key never updates). Scope: caches are branch-scoped; a branch reads its own + base/default branch caches, not sibling branches. ~10 GB/repo LRU eviction. `setup-*` `cache:` wraps this.

## Artifacts (files between jobs / retained)
```yaml
- uses: actions/upload-artifact@v4
  with: { name: dist, path: dist/, retention-days: 7 }
- uses: actions/download-artifact@v4     # in a needs: job
  with: { name: dist }
```
- v4 artifacts are immutable (can't re-upload same name in one run) and downloadable mid-run (unlike v3). Retention default 90d.

## Secrets & OIDC
- Scopes: repo / org / **environment**. Read via `${{ secrets.NAME }}`; auto-masked in logs but reconstructable — never `echo`, pass via `env:` not CLI args.
- **OIDC (preferred over long-lived cloud creds)**: `permissions: { id-token: write }` then `aws-actions/configure-aws-credentials` / `google-github-actions/auth` exchange a short-lived signed token for temporary cloud creds via a trust policy scoped to the repo/branch/environment. No stored `AWS_ACCESS_KEY_ID`.
- `GITHUB_TOKEN`: auto-provisioned per run, expires at job end.

## Permissions (least-privilege `GITHUB_TOKEN`)
```yaml
permissions:
  contents: read          # start minimal
  # add per-need: packages: write, id-token: write, pull-requests: write
```
- Set at workflow or job level; job overrides workflow. Default can be write-all on older repos — declare explicitly.

## Concurrency
```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true      # supersede in-flight runs on the same ref
```
- Serializes/cancels runs sharing a group — prevents overlapping deploys / redundant PR builds.

## Reusable & composite workflows
- **Reusable** (`on: workflow_call`): a whole callable workflow (own jobs/runners) invoked via `uses: org/repo/.github/workflows/x.yml@sha` with `with:`/`secrets:` (or `secrets: inherit`).
- **Composite**: an action bundling steps (`runs.using: composite`) that inlines into a job — no separate runner. Use composite to DRY steps, reusable workflow to DRY jobs.

## Environments
- `environment: production` gates a job behind **required reviewers**, wait timers, branch restrictions, and env-scoped secrets/vars. Deployment approval UI + protection rules.

## Conditionals & contexts
- `${{ }}` expressions: `github.*` (ref, sha, event_name, actor, base_ref), `env.*`, `secrets.*`, `vars.*`, `matrix.*`, `needs.*`, `steps.*`, `runner.*`.
- `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`. Functions: `contains()`, `startsWith()`, `success()`, `failure()`, `always()`, `cancelled()`.

## Full example
```yaml
name: CI
on: { push: { branches: [main] }, pull_request: {} }
permissions: { contents: read }
concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm test
```

## Gotchas -> Fix
- **Fork-PR secret theft / privilege escalation**: `pull_request` from a fork gets **no secrets + read-only token** (correct default). `pull_request_target` runs the **base** workflow with secrets + write token — NEVER check out/run untrusted fork code under it; gate with `environment` approval or label checks.
- **Script injection via `${{ }}`**: interpolating `github.event.*.title/body/*_ref` straight into `run:` lets attackers inject shell — pass untrusted input through `env:` and reference `"$VAR"`, never inline `${{ github.event.pull_request.title }}` in a script.
- **Over-broad token**: default write-all -> set explicit minimal `permissions:`; widen per job.
- **Unpinned actions**: `@v4`/branch tags are mutable (hijack risk) -> pin third-party to full SHA; enable Dependabot for action bumps.
- **Cache never updates / stale deps**: keys are immutable — a lockfile change must alter `hashFiles` in the key, or you keep restoring old deps; use `restore-keys` for partial hits.
- **Cache not shared across PRs**: branch scoping means feature branches only see their own + default-branch cache — warm the cache on `main`.
- **Matrix explosion**: dimensions multiply into minutes/cost -> trim with `exclude`, `max-parallel`, or run full matrix only on `main`.
- **`ubuntu-latest` drift**: image contents change over time and can break builds -> pin `ubuntu-24.04` for reproducibility.
- **`needs` job runs on upstream failure**: a downstream `if:` is evaluated even after failure -> add `if: success()` (or `always()` intentionally).
- **Secrets don't reach reusable workflow**: not inherited automatically -> pass `secrets: inherit` or explicit `secrets:`.
- **`GITHUB_TOKEN` push doesn't trigger other workflows**: events from the default token don't re-trigger workflows (loop prevention) -> use a PAT/App token if you need chaining.
