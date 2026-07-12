# Software Engineering Reference

## Structuring a change
- Smallest diff that fully solves it; don't reformat unrelated lines — noise hides the real change in review.
- Match local conventions (naming, error style, imports) over personal preference. Grep a sibling file first.
- One concern per commit/PR. Mixing a refactor with a behavior change makes both unreviewable.
- **Incremental delivery** beats big-bang: ship thin vertical slices behind a **feature flag**; integrate continuously. A big-bang merge/rewrite fails late and unrecoverably.

## SDLC & process
- Flow: **requirements -> design -> implement -> test -> deploy -> maintain/operate**. Cost to fix a defect rises ~10x per phase it survives — catch it early (review > test > prod).
- **Agile/iterative** (short loops, working software, feedback) vs **waterfall** (fixed sequence). Iterate when requirements are uncertain; the point is shortening the feedback loop, not ceremony.
- Requirements: capture the **problem and acceptance criteria**, not a solution. Nail the "what/why" before the "how"; ambiguous requirements are the top source of rework.
- **Estimation**: estimate small, decomposed tasks; give ranges/confidence not points; track actual vs estimate to calibrate. Beware the **planning fallacy** (systematic under-estimate); add buffer for integration, testing, unknowns.

## Clean code
- **Naming**: name for meaning, not construction (`activeUsers`, not `filteredList`). Booleans read as predicates (`isReady`). Consistent, searchable, no misleading names.
- **Small functions**: one job, one level of abstraction, few params. Prefer early return over deep nesting.
- **High cohesion, low coupling**: related things together; minimize what modules know about each other. Depend on interfaces, hide internals.
- Comments explain **why**, not what; code says what. Delete commented-out code — that's what VCS is for.

## Error handling
- **Fail loud** on programmer errors / violated invariants (bad args, impossible states): raise/throw, don't return null.
- **Degrade** only on expected external failures (network, missing file) and only where you can act — retry, fallback, or a clear message.
- Catch at the **boundary** where you have context to handle it, not the throw site. Never `catch {}` swallow; at minimum log with cause.
- Validate inputs at the API boundary, then trust them inward.

## API & function design
- Explicit contracts: narrow types over `any`/`dict`, enums over magic strings, non-null over optional-everywhere.
- Return one type per function; pick a documented sentinel, don't return `T | false | null`.
- No boolean-trap params (`f(true, false)`) — keyword args / options object.
- Pure core, side effects at the edges — easier to test and reuse.

## Testing
- **Test pyramid**: many fast **unit** tests, fewer **integration**, few **E2E**. Inverted (mostly E2E) = slow, flaky, brittle CI.
- Test **behavior/contracts**, not implementation — else every refactor breaks tests. Assert on outcomes.
- One reason to fail per test; deterministic (no real time/network/randomness — fake them). **Red-green-refactor** (TDD) when the design is unclear.
- **Characterization tests** pin legacy behavior before you touch it. Coverage is a smoke detector, not a goal; 100% of trivial getters proves nothing.
- Test edge/boundary cases and failure paths, not just the happy path.

## Refactoring safely
- Tests green BEFORE you touch it. No tests? Add a characterization test first.
- Behavior-preserving steps; run tests between each. Don't refactor and add features in one move.
- **Rule of three**: inline until the third duplication. A wrong abstraction costs more than copy-paste — prefer a little duplication over a leaky base class.

## Version control discipline
- Small, atomic, **self-describing commits**; message says *why*. Keep `main` releasable/green.
- Short-lived branches; integrate often to avoid merge hell. Trunk-based or short PR branches over long-lived forks.
- Never rewrite shared/published history. Feature flags decouple deploy from release.

## Debugging method
- **Reproduce** reliably first; a bug you can't reproduce you can't fix or verify fixed.
- **Bisect** the search space: `git bisect`, binary-search the input, disable half the code. Read the actual error/stack; don't guess.
- Form a hypothesis, change **one thing**, observe. Question assumptions — verify what you "know" is true. Add logging/asserts/a failing test that captures the bug, then fix.
- Fix the **root cause**, not the symptom. Add a regression test so it can't return.

## Code review
- Review for **correctness, security, design, readability, tests** — not style a linter/formatter should catch.
- Small PRs get real review; huge PRs get rubber-stamped. Comment on the code, not the author; ask, don't demand.
- Red flags: functions >~40 lines, >3 nesting levels, unused params, TODO with no ticket, commented-out code, swallowed errors, off-by-one at loop bounds, no test for new behavior.

## Delivery & operations
- **CI**: every push builds + runs the test suite; keep it fast and green. **CD**: automated, repeatable deploys; small frequent releases reduce blast radius and make rollback cheap.
- **Progressive rollout**: canary / blue-green / feature flag; watch metrics, roll back fast. Decouple deploy (shipping code) from release (enabling behavior).
- **Observability**: logs (structured), metrics, traces. You can't operate what you can't see. Alert on symptoms users feel (error rate, latency), not every internal blip.
- **Blameless postmortems** on incidents: fix the system/process, not the person; add a regression test/guardrail.

## Tech debt & documentation
- Take debt **knowingly** with a ticket/comment naming the tradeoff; refuse it silently in core paths costly to change later. Distinguish deliberate/prudent debt from sloppiness.
- Document the **why/decisions** (ADR, README, design doc), interfaces, and runbooks — not line-by-line what. Docs rot; keep them near the code and minimal.

## Working in teams / pitfalls -> Fix
- **Big-bang integration/rewrite** -> integrate continuously; ship incremental slices behind flags.
- **No / only-happy-path tests** -> pyramid of behavior tests incl. edges + failure paths before shipping risky change.
- **Cargo culting** (copying patterns without understanding) -> know *why*; delete ceremony that adds no value.
- **Bikeshedding** (arguing trivia, ignoring hard core) -> timebox trivia, let linter/formatter decide style, focus on substance.
- **Gold-plating** (features/abstraction nobody asked for) -> YAGNI; build to the requirement.
- **Hero/bus-factor-1** (one person owns critical knowledge) -> review, pair, document, share ownership.
- **Not-invented-here / reinventing** -> use the stdlib/proven lib for solved problems; save novelty for the actual problem.
- **Broken-windows neglect** -> fix small rot early; disorder compounds.
- **Estimate treated as commitment** -> communicate ranges + assumptions + risk; re-forecast as you learn.
