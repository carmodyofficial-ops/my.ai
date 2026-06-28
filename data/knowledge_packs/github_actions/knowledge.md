# GitHub Actions CI/CD Reference

## File Location
- Workflows live in `.github/workflows/*.yml` (one file = one workflow). Top-level keys: `name`, `on`, `permissions`, `jobs`.

## Triggers (`on:`)
```yaml
on:
  push: { branches: [main], paths: ['src/**'] }
  pull_request: { branches: [main] }
  schedule: [{ cron: '0 6 * * 1' }]   # UTC, min-granularity 5m
  workflow_dispatch:                  # manual run button + inputs
```
- `paths`/`branches` (and `-ignore` variants) filter when it runs.

## Jobs
- Jobs run **in parallel** by default; serialize with `needs:`.
- Each job runs on a fresh VM: `runs-on: ubuntu-latest`.
```yaml
jobs:
  build: { runs-on: ubuntu-latest, steps: [...] }
  deploy: { needs: build, runs-on: ubuntu-latest, steps: [...] }
```

## Steps
- `uses:` runs a published action; `run:` runs shell. `with:` passes inputs.
- Pin actions to a tag or **full SHA** (supply-chain safety).
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4
    with: { node-version: 20, cache: npm }
  - run: npm ci && npm test
```
- Common: `actions/checkout@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`.

## Matrix
```yaml
strategy:
  fail-fast: false
  matrix: { node: [18, 20, 22], os: [ubuntu-latest, windows-latest] }
runs-on: ${{ matrix.os }}
```
- `fail-fast: false` keeps other combos running after one fails.

## Contexts & Expressions
- `${{ }}` evaluates: `github.*` (ref, sha, event_name, actor), `env.*`, `secrets.*`, `matrix.*`.
- Conditionals: `if: github.ref == 'refs/heads/main'`, `if: github.event_name == 'push'`.

## Secrets
- Repo/org/environment scoped; read via `${{ secrets.NAME }}`. `GITHUB_TOKEN` is auto-provided.
- Never `echo` a secret; masked in logs but reconstructable. Pass via `env:`, not args.

## Caching
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: npm-
```

## Artifacts (pass files between jobs)
```yaml
- uses: actions/upload-artifact@v4
  with: { name: dist, path: dist/ }
- uses: actions/download-artifact@v4   # in a needs: job
  with: { name: dist }
```

## Permissions (least-privilege)
```yaml
permissions:
  contents: read        # default-minimal; widen per job as needed
```

## Environments
- `environment: production` gates a job behind required reviewers / wait timers / env secrets.

## Full Example
```yaml
name: CI
on: { push: { branches: [main] }, pull_request: {} }
permissions: { contents: read }
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
- **Fork PR secrets unavailable**: `pull_request` from forks gets no secrets + read-only token. Use `pull_request_target` only with extreme care (it runs base-repo code with secrets against untrusted PRs — never checkout/run fork code).
- **Over-privileged token**: set explicit `permissions:` (default can be write-all).
- **Unpinned actions**: pin to full commit SHA; `@v4` tags are mutable.
- **No dep caching**: slow, costly builds — add `actions/cache` or `setup-*` `cache:`.
- **Matrix explosion**: dimensions multiply -> minutes/cost; trim combos, use `include`/`exclude`.
- **`latest` runner drift**: `ubuntu-latest` image changes can break builds; pin (`ubuntu-24.04`) for reproducibility.
