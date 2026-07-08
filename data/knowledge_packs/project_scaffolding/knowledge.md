# Project Scaffolding
## Layout conventions
- Python: src layout — `src/pkg/`, `tests/` outside it, `pyproject.toml` at root. Why src: tests import the *installed* package (`pip install -e .`), not the cwd copy, so packaging bugs surface locally instead of in prod. Never `sys.path` hacks.
- Frontend: feature folders over type folders — `features/checkout/{components,hooks,api,types}.ts` beats top-level `components/`, `hooks/` buckets once the app passes ~10 screens; shared primitives live in `shared/` or `ui/`. Deleting a feature = deleting one folder.
- Node service: `src/` with `routes/` (or `api/`), `services/` (logic), `db/` or `repos/` (persistence), `config.ts`; compiled output to `dist/`, never committed.
- Universal root set: `README.md`, `.gitignore`, `.editorconfig`, lockfile, task runner file, `LICENSE` (if public), `.env.example` (never `.env`).

## Config layering
- Precedence: CLI flags > env vars > config file > defaults — each layer overrides the previous; document the order in README.
- Read config ONCE at startup into a typed object (pydantic `BaseSettings` / zod-parsed `process.env`); crash immediately on missing/invalid values — a service that boots with bad config fails at 3am instead of deploy time.
- `.env` for local dev only (gitignored), `.env.example` committed with every key and a dummy value; real secrets come from the environment/secret manager, never files in the repo.
- No config reads scattered through the codebase — `os.environ[...]` deep in business logic is untestable and undiscoverable.

## Dependencies
- Lockfiles are non-negotiable and committed: `uv.lock`/`poetry.lock` (Python apps), `package-lock.json`/`pnpm-lock.yaml`. Loose ranges in the manifest, exact pins in the lock.
- Libraries: wide version ranges in metadata, no lockfile shipped to consumers (dev lockfile fine). Apps: reproducible installs via `npm ci` / `uv sync --frozen` in CI — never bare `install`, which can rewrite the lock.
- Separate dev deps from runtime deps (`[dependency-groups]`/`--group dev`, `devDependencies`); prod images install runtime only.

## Task runner
- One entry point for every workflow: Makefile or justfile with `setup`, `test`, `lint`, `fmt`, `run`, `build`. New contributor path is `make setup && make test`, no tribal knowledge.
- CI calls the same targets developers do — otherwise "passes locally, fails in CI" is designed in.
- Makefile gotcha: recipes need TABS not spaces; declare non-file targets `.PHONY`. justfile avoids both and takes arguments cleanly.

## Gotchas -> Fix
- **Works locally, breaks installed**: flat layout let tests import the source tree directly. Fix: src layout + editable install; run tests in CI from a clean `pip install .` at least once.
- **"npm install" in CI produced different deps than local**: install can update the lock. Fix: `npm ci` (or `pnpm install --frozen-lockfile`) in CI — fails on drift instead of hiding it.
- **Secrets committed in `.env`**: Fix: `.env` in `.gitignore` *before* first commit; add secret-scanning (gitleaks) pre-commit; rotate anything that ever landed in history — deleting the file does not delete the commit.
- **Formatter and linter fight**: eslint reformatting against prettier. Fix: prettier owns formatting, eslint owns correctness — use `eslint-config-prettier` to disable stylistic eslint rules. Python: ruff does both (`ruff format` + `ruff check`), one tool, one config.
- **Config value read as string "false" is truthy**: env vars are always strings. Fix: parse booleans/ints explicitly at the boundary (pydantic/zod coercion), never `if os.environ.get("FLAG"):`.
- **Monorepo adopted too early**: one small app gains workspace tooling overhead. Fix: monorepo when code is *shared* across deployables or teams need atomic cross-cutting changes; until then one repo per deployable. If yes: pnpm workspaces / uv workspaces, shared lint config package, per-package `test` targets, CI that builds only affected packages.
- **README rot**: setup steps drift. Fix: README's setup section is just "run `make setup`" — the executable doc can't rot silently because CI runs it.

## Baseline tooling
- `.editorconfig`: `indent_style`, `end_of_line = lf`, `insert_final_newline = true`, `trim_trailing_whitespace = true` — settles cross-editor wars in 8 lines.
- Python: ruff (lint+format, replaces flake8/isort/black), pyright or mypy, pytest; configure all in `pyproject.toml`.
- TS/JS: eslint (typescript-eslint) + prettier + `tsc --noEmit` in CI; `"strict": true` in tsconfig from day one — retrofitting strict is a project.
- Pre-commit hooks (pre-commit / husky+lint-staged) run format+lint on changed files only; CI re-runs on everything as the backstop.

## CI skeleton
- Minimum viable pipeline, on every PR: checkout -> setup runtime (pinned version) -> restore dep cache keyed on lockfile hash -> frozen install -> lint -> typecheck -> test. Under ~5 min or people stop waiting for it.
- Pin action/runner versions; matrix over supported runtimes only if you actually support several.

## Starting templates
- README essentials: one-sentence purpose, quickstart (3 commands max), config table (var/default/meaning), how to run tests, where to get help.
- Python CLI: `pyproject.toml` with `[project.scripts] mycli = "pkg.cli:main"`, argparse/typer, src layout, `--version` flag, exit codes (0 ok, nonzero failure), logs to stderr / output to stdout.
- FastAPI service: `src/app/{main.py,routers/,services/,models/,settings.py}` (pydantic-settings), `/healthz` route, uvicorn entry, Dockerfile (slim base, non-root user, frozen install), httpx-based tests via `TestClient`.
- React app: Vite scaffold, feature folders, react-router, typed API client in `shared/api/`, vitest + testing-library, `.env` vars must be prefixed `VITE_` to reach the client.
- Node service: TS strict, `tsx` for dev / compiled `dist` for prod, zod-validated env in `config.ts`, pino logging, graceful shutdown on SIGTERM (finish in-flight, close server, then pool).

## Checklist before first feature
- `.gitignore` covers: `.env`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `.pytest_cache/`, coverage output, editor cruft (`.idea/`, `.vscode/` unless shared settings are intentional).
- One smoke test exists and CI runs it — an empty test suite means the pipeline proves nothing; `test_import` / render-the-root-component is enough on day one.
- Runtime version pinned and visible: `.python-version` / `requires-python` in pyproject; `"engines"` + `.nvmrc` for Node — CI and local must agree or "works locally" is luck.
- Logging configured once at the entrypoint (level from env, structured in prod, human-readable in dev); libraries get a logger (`logging.getLogger(__name__)`) and never call `basicConfig` or add handlers.
- Version single-sourced: `pyproject.toml` `[project] version` read via `importlib.metadata.version("pkg")`; `package.json` version — not duplicated in a `__version__` string that drifts.
- Decide test layout now: `tests/` mirroring `src/` (Python default) or colocated `*.test.ts` next to source (frontend default) — migrating later touches every file.
- Empty-dir placeholders: git doesn't track empty directories; drop a `.gitkeep` if the layout matters before content exists.
- Dependabot/Renovate config from day one — dependency updates arrive as small weekly PRs instead of a terrifying quarterly bump.
