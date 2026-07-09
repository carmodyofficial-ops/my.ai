# Agent-Ready Work Items
## Agent story vs human story
- A human story is a **conversation placeholder** (Card/Conversation/Confirmation); an agent story is a **self-contained brief** — the agent won't tap a hallway PM for the missing bit.
- Agents need **explicit paths, commands, and a machine-checkable done**; drop the business narrative that a human infers, keep the operational specifics.
- Human AC = "user can reset password". Agent AC = "`POST /auth/reset` returns 202; `pytest tests/auth/test_reset.py` passes; no new `ruff` errors".
- Optimize for: **unambiguous scope**, **runnable verification**, **guardrails**, **enough context to not guess**, **fits one session**.
- The agent will do EXACTLY what you wrote and nothing you implied. Underspecify -> it flails or over-reaches; no check -> it declares false "done".
## Precise scope (explicit paths/modules)
- Name the **files/dirs/modules** to change: `src/api/auth.py`, `src/models/user.py`. Name what's **out of scope**.
- State the **entry point** and the **symbols** involved: function `validate_token()`, class `SessionStore`.
- One coherent change per item — a slice an agent can hold in context start to finish.
- Prefer "edit these 3 files" over "refactor the auth system".
## Repro steps (for bugs)
- Exact **command + input + observed vs expected** output. Deterministic, copy-pasteable.
```
Repro:
  1. `curl -s localhost:8000/api/orders/999`
  2. Observed: HTTP 500, `KeyError: 'total'` in orders.py:142
  3. Expected: HTTP 404 `{"error":"order not found"}`
Env: main @ abc1234, python 3.11, `make dev` running
```
- Include stack trace, failing test name, log line, or seed. If flaky, say so and give repeat count.
## Verification-first (define done as an observable check)
- Write the **check before the change**. Done = the check flips from fail to pass. Forms:
  - **Failing test to make pass**: "make `tests/test_reset.py::test_expired_token` pass (currently red)". Best signal — write the test in the item if it doesn't exist.
  - **CLI/HTTP command + expected output**: `curl ... | jq .status` -> `"ok"`.
  - **Build/lint/typecheck gate**: `npm run build && npm run typecheck && npm run lint` all exit 0.
  - **Observable behavior**: log line appears, file created, row written, exit code 0.
- Verification must be **runnable by the agent itself**, deterministic, and not self-gradeable by narrative ("looks correct" is not a check).
```
Done when:
  - `pytest tests/auth/test_reset.py` -> all green
  - `ruff check src/auth/` -> 0 errors
  - `curl -XPOST localhost:8000/auth/reset -d '{"email":"a@b.c"}'` -> HTTP 202
```
## Verification tiers (strongest first)
- **Automated test** (unit/integration) named in the item — deterministic, re-runnable, the gold standard. Prefer TDD-style: write/point at the red test, done = green.
- **Command + exact expected output**: `curl`, CLI, script -> specific stdout/status/exit code.
- **Gate command**: build/lint/typecheck/format-check exit 0 (regression guard, not proof of feature).
- **Observable side effect**: file/row/log/artifact created, asserted by a follow-up command.
- **Human review** — last resort, only for genuinely un-automatable judgment; mark it explicitly so the agent doesn't self-grade.
## Machine-verifiable acceptance criteria
- Each AC maps to a **command whose output decides pass/fail**. No "should feel fast" — say "p95 < 200ms via `bench.sh`".
- Bind AC to concrete artifacts: exact status code, exact JSON shape, exact exit code, named test.
- If a criterion can't be turned into a command, either add tooling to make it checkable or mark it "human-review only" explicitly.
## Guardrails
- **Do NOT touch**: list files/dirs off-limits — `migrations/`, `infra/`, `*.lock`, generated code, unrelated modules.
- **No scope creep**: "fix only the null check; do not refactor surrounding code / rename / reformat unrelated lines."
- **Safety boundaries**: no network calls to prod, no secrets in code, no deleting data, no force-push, no new dependencies without approval.
- **Don't fabricate**: if a fact/API/file is unknown, stop and ask — do not invent endpoints, config keys, or test data. No fake green (don't skip/delete the failing test to "pass").
- **Respect conventions**: match existing style/patterns; run the formatter, don't hand-roll one.
## Context to provide
- **Relevant files** to read first (even if not edited): the interface it implements, the caller, the model.
- **Prior art / examples**: "mirror `src/api/login.py` for structure and error handling."
- **Conventions**: error format, logging, naming, test layout, dependency-injection pattern.
- **Fixtures/commands**: how to run the app (`make dev`), run tests (`pytest -q`), seed data.
- Just enough — over-stuffing context dilutes attention as much as too little.
## Right-sizing to one session
- Fits in **one coherent agent session**: bounded files, single objective, verifiable at the end — before context loss degrades quality.
- Too big signal: touches many unrelated modules, needs several independent verifications, or you can't state one done check. Then **split into sub-tasks**, each independently verifiable, sequenced.
- Each sub-task: own scope + own verification. Chain them; don't nest a mega-task.
## Handling ambiguity
- **Encode the decision** in the item ("on conflict, last-write-wins") OR add an explicit **"ASK FIRST: ..."** gate for the unknown.
- Never leave a fork silent — the agent will pick one arbitrarily and confidently. Default behaviors must be stated.
- For irreversible/risky choices (schema change, data delete, API contract): require confirmation before acting.
## Plan -> implement -> verify loop
- **Plan**: agent restates scope, lists files it will touch, states the verification it will run. Cheap to correct here.
- **Implement**: minimal change to satisfy the check; stay inside guardrails.
- **Verify**: run the defined check; on red, iterate; on green, stop. Report the command output as evidence.
- Bake the loop into the item: "before editing, list the files you'll change and the test you'll run."
## Sub-task chaining (when one item is too big)
- Break into an **ordered chain**, each link independently verifiable and shippable in a session.
```
Epic: add rate limiting to the API
  T1: add token-bucket util  -> `pytest tests/test_bucket.py` green
  T2: wire middleware on /api/*  -> `curl` 60 reqs -> 429 after limit
  T3: return Retry-After header  -> header present, integration test green
  T4: make limits config-driven  -> env override respected, test green
```
- Each link states which prior link's output it consumes. Don't nest; keep it flat and sequenced.
- If two links must land together atomically, they're one item — merge them.
## What the agent should report back
- The **command(s) run** and their **actual output** (exit codes, test summary) — evidence, not narration.
- **Files changed** (diff or list), matched against the declared scope.
- Any **guardrail hit** or **assumption made** ("no version file found, used git tag — confirm?").
- Explicit **red/green** on each Done-when check. "I believe it works" is not acceptance.
## Conventions & prior art (reduce guessing)
- Point at a **canonical example**: "structure this like `src/api/login.py`" beats prose describing structure.
- State the **error/response contract** once: shape, status codes, logging format, naming.
- Give the **commands** up front: run app, run tests, lint, typecheck, seed — so the agent verifies without inventing.
- Note **framework/version** quirks the agent might get wrong (e.g., "Pydantic v2, not v1").
## Template
```
Title: <imperative, one behavior>
Type: bug | feature | chore
Scope (edit): <explicit file paths / symbols>
Out of scope / DO NOT TOUCH: <paths, patterns>
Context (read first): <files, prior-art example, conventions>
Repro (bugs): <cmd -> observed vs expected, env/commit>
Change: <what to make true, not how, unless how matters>
Verification (Done when):
  - <cmd + expected output / exit code>
  - <named test goes green>
  - <build/lint/typecheck pass>
Guardrails: <no new deps / no refactor / ask-first on X / no fabrication>
Ambiguity: <encoded decision, or "ASK FIRST: ...">
```
## Worked example — bug fix
```
Title: Return 404 (not 500) for missing order
Type: bug
Scope (edit): src/api/orders.py (get_order handler ~line 138)
Out of scope: src/models/*, migrations/, tests fixtures schema
Context: mirror not-found handling in src/api/users.py:get_user
Repro:
  `curl -s localhost:8000/api/orders/999` -> HTTP 500 KeyError 'total'
  Expected -> HTTP 404 {"error":"order not found"}
  Env: main @ abc1234, `make dev`
Change: guard the missing-order case before dict access; raise NotFound.
Done when:
  - `pytest tests/api/test_orders.py::test_missing_order_404` -> green (add this test)
  - `curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/orders/999` -> 404
  - `ruff check src/api/orders.py` -> 0 errors
Guardrails: touch only get_order; no signature changes; no new deps.
```
## Worked example — small feature
```
Title: Add GET /health endpoint
Type: feature
Scope (edit): src/api/app.py (register route), src/api/health.py (new)
Context: route style in src/api/orders.py; JSON error shape in src/api/errors.py
Change: GET /health returns 200 {"status":"ok","version":<__version__>}
Done when:
  - `curl -s localhost:8000/health | jq -r .status` -> ok
  - `pytest tests/api/test_health.py` -> green (add test asserting 200 + shape)
  - `npm run typecheck` n/a; `ruff check src/api/` -> 0
Guardrails: no auth on this route; no DB access; do not modify existing routes.
Ambiguity: version source = src/__init__.py __version__ (do not hardcode).
```
## Pitfalls -> Fix
- **Underspecified scope -> agent flails/over-reaches**: "improve auth". Fix: name exact files/symbols and the out-of-scope list.
- **No verification -> false "done"**: agent says "fixed" with nothing run. Fix: define a runnable check; done = check passes, with output pasted as proof.
- **Too big -> loses coherence/context**: sprawls across many modules mid-session. Fix: split into sub-tasks, each with its own scope + check.
- **Vague "improve X" / "make it better"**: no target state. Fix: state the observable end condition and its command.
- **No guardrails -> touches unrelated code**: reformats the repo, renames things. Fix: explicit DO-NOT-TOUCH list + "no refactor beyond the change".
- **Ambiguous acceptance the agent self-grades as pass**: "handles errors gracefully". Fix: machine-checkable AC (exact status/JSON/test), not prose judgment.
- **Silent fork in requirements**: two valid interpretations, none chosen. Fix: encode the decision or add "ASK FIRST".
- **Fabricated facts**: invented endpoints/config/test data to look complete. Fix: "if unknown, stop and ask; do not invent" + provide the real references.
- **Fake green**: agent deletes/skips the failing test to pass. Fix: forbid test edits except adding the specified one; verify the test still asserts the behavior.
- **Context dump**: 40 files "for reference". Fix: list only the few that matter, with why (read-for-pattern vs edit).
- **How over-specified, boxing the agent**: prescribing exact code when only the outcome matters. Fix: specify the observable outcome; leave implementation negotiable unless a convention is mandatory.
