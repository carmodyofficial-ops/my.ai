# Testing Strategy and Regression Design

## Test Pyramid & Layer Choice
- Pyramid: many fast unit tests -> fewer integration tests -> few end-to-end/smoke. Cost, runtime, and flakiness all rise as you go up; debugging precision falls.
- Unit: one behavior, no I/O, milliseconds — best for logic, edge cases, error paths. Integration: real components wired together (route + service + DB) — best for contracts, serialization, config, SQL. E2E/smoke: the deployed thing actually answers — few, critical paths only.
- Choose the LOWEST layer that can actually catch the bug class. Auth wiring, middleware order, ORM mappings, and route registration live at integration level — unit tests structurally cannot catch them.
- A passing compile/import check only proves syntax; a passing unit suite with mocked boundaries proves nothing about wiring. Every layer answers a different question — name which question a test answers.
- Full ladder for a service: compile/import check -> unit -> integration -> containerized run against the working tree -> live smoke (running service) -> network smoke (LAN URL) -> physical-device smoke.
- Known good containerized pattern: run tests in the project's Docker image with `--entrypoint python` (skip entrypoint side effects), mounting the host tree: `-v "$PWD":/workspace -w /workspace -e PYTHONPATH=/workspace`.

## Regression Tests from Bug Reports
- Every real bug gets a test that FAILS on the pre-fix code and passes after. Write it first, watch it fail — a regression test that never failed proves nothing.
- Encode the bug's trigger conditions exactly (input, state, sequence), not a paraphrase. Name it after the defect: `test_guest_cannot_be_promoted_to_admin`, optionally with the issue ID.
- Test the SYMPTOM at the boundary where it was observed (API response, file output), not the internal function you happened to fix — the internal may be refactored away; the behavior contract stays.
- Generalize one step: if off-by-one at `n=0`, also test `n=1`, boundary, and huge; bugs cluster at boundaries.
- Lesson learned in-house: regression tests caught that Guest could still be promoted to admin; a passing compile would never have caught it.

## Negative Tests (test what MUST NOT happen)
- Security/permission suites are mostly negative tests: guest cannot access admin endpoints; guest cannot be promoted; guest cannot invoke bash/agent/memory management; reserved usernames cannot be created; the last admin cannot be removed.
- Assert on the refusal itself: expect 403/error AND assert no side effect occurred (row unchanged, file absent). A negative test that only checks the status code misses "denied but still executed".
- For every "X can do Y" test, ask "who must NOT be able to do Y?" and write that too.

## Mocking Discipline
- Mock at BOUNDARIES you don't own (HTTP APIs, clock, filesystem, payment gateway, email), never internals of the code under test. Mocking your own private functions welds tests to implementation — refactors break tests while behavior is unchanged.
- Prefer fakes (in-memory repo implementing the real interface) over mock-object assertion chains; fakes survive refactors.
- Verify state/outputs, not call sequences, unless the call IS the contract (e.g., "sends exactly one email").
- Every mocked contract needs at least one real-thing test elsewhere (contract/integration test), or the mock drifts from reality and everything passes while prod fails.
- Always mock: time (`freezegun`/injected clock), randomness (seed or inject), network to third parties. Almost never mock: your own DB in integration tests — use a real ephemeral one (Docker/testcontainers/SQLite where honest).

## Fixtures & Factories
- Factories build valid objects with overridable fields: `make_user(role="guest")` — test bodies show ONLY the fields that matter to that test.
- Keep fixtures minimal and local; a giant shared `conftest.py` god-fixture couples every test to every field. Compose small fixtures instead.
- Fresh state per test: transaction-rollback or truncate per test; never depend on data left by a previous test (ordering coupling = flake factory).
- Builders beat frozen JSON blobs: a stored blob rots when the schema changes; a factory updates in one place.

## Flaky Tests: Causes -> Fixes
- **Time/sleep-based waits** -> poll for the condition with timeout ("wait until X or 5 s"), inject clock; never bare `sleep(2)`.
- **Shared mutable state / test-order dependence** -> isolate per test (fresh DB tx, tmp dirs, reset singletons); run in random order to detect.
- **Concurrency/races in the code itself** -> the flaky test found a real bug; fix the code, don't retry-mask it.
- **External network calls** -> stub/record-replay; hermetic tests only in CI.
- **Unordered collections asserted as ordered** -> sort before comparing or assert set-equality.
- **Floating point equality** -> `pytest.approx` / epsilon compare.
- **Ports/files/global registries colliding under parallel runs** -> ephemeral ports (bind 0), unique tmp paths per test.
- Policy: quarantine + ticket immediately; a suite people rerun-until-green is dead — retries hide real races, so cap and log them.

## Coverage Pitfalls
- Line coverage measures execution, not verification: a test with zero asserts can hit 100%. Assertion quality > coverage number.
- Branch coverage > line coverage; error paths and `except` blocks are where uncovered bugs live.
- Coverage targets as a gate invite padding (tests that call code and assert nothing). Use coverage DIFFS on changed lines in review instead of a global bar.
- 100% coverage still misses: wrong requirements, missing code (the `if` you never wrote), concurrency, config/wiring, and data-dependent bugs. Mutation testing (`mutmut`, `pitest`) measures whether tests actually detect changes.

## Property-Based Testing
- Instead of examples, state invariants and let the framework generate inputs (`hypothesis` in Python, `fast-check` in JS): `@given(st.lists(st.integers()))` then assert `sorted(xs)` is ordered and a permutation of `xs`.
- Classic properties: round-trip (`decode(encode(x)) == x`), invariants (length preserved, non-negative), idempotence (`f(f(x)) == f(x)`), oracle (fast impl matches brute force), metamorphic (adding an item never lowers the total).
- Shrinking auto-minimizes failing inputs — commit the found counterexample back as a pinned regression example.
- Best on parsers, serializers, math/date logic, state machines; poor on I/O-heavy glue.

## Test Design Heuristics
- One behavior per test; name = behavior sentence (`test_expired_token_rejected`), not `test_1`.
- Arrange-Act-Assert with a single Act; multiple unrelated asserts hide which behavior broke.
- Boundaries first: empty, one, many, max, max+1, zero, negative, unicode, duplicate, None/null, already-exists, concurrent-double-submit.
- Determinism is non-negotiable: pin seeds, freeze time, sort outputs.
- Fast suite or unused suite: unit suite under ~30 s keeps people running it pre-commit; move slow tests behind a marker (`-m "not slow"`), run full ladder in CI.

## Gotchas -> Fix
- **Regression test written after the fix, never seen failing** -> `git stash` the fix (or invert assert) to confirm it fails, then restore.
- **Mocked test passes, prod broken** -> add an integration/contract test hitting the real dependency; mocks drifted.
- **Negative test asserts status only** -> also assert absence of side effect.
- **Suite green only in full-run order** -> randomize order (`pytest -p randomly`), fix shared state.
- **Testing internals (private methods, call counts)** -> test through the public API; assert outcomes.
- **Snapshot/golden tests blindly re-approved** -> keep snapshots small and reviewed; giant snapshots = rubber-stamp updates.
- **High coverage, low confidence** -> mutation-test a critical module; add asserts where mutants survive.
- **Sleep-driven async test** -> event/condition polling with deadline.
- **Fixture god-object breaks 200 tests per schema change** -> factories with defaults + per-test overrides.
