# Definition of Ready & Done

## Core distinction
- **DoR** = entry gate: is this story safe to **pull** into a sprint? Guards against starting work that stalls mid-sprint.
- **DoD** = exit gate: is this story actually **finished**? Guards against "done" meaning "code compiles on my machine".
- Both are **team working agreements** (checklists the team owns and edits), not company policy imposed top-down. Same across all stories in a team; per-team customization expected.
- DoR is the **implementability gate**: if a dev can't start without asking a clarifying question, it's not Ready.
- DoD makes "done" mean **"done done"** — shippable increment, not "dev-complete, QA later".

## Definition of Ready (checklist)
```
[ ] Value clear — user/business benefit stated (the "so that")
[ ] Acceptance criteria present, unambiguous, and TESTABLE (pass/fail objective)
[ ] Sized — team estimated it; not >1 sprint (else split)
[ ] Dependencies identified AND resolved/sequenced (no "blocked by unknown")
[ ] No blocking unknowns — spikes done; open questions have answers or owners
[ ] Designs/mocks ready for UI work (states + validation linked)
[ ] Technical approach agreed enough to start (contracts/interfaces known)
[ ] Test approach known (how each AC gets verified)
[ ] Small enough to demo — a thin vertical slice, not a layer
[ ] Team confident they can start today without a clarifying question
```
- Apply at backlog refinement, BEFORE sprint planning — keep ~1–2 sprints of Ready stories at top of backlog.
- A story failing DoR goes back to refinement, not into the sprint.

## Definition of Done (checklist)
```
[ ] Code complete — meets AC, follows team conventions
[ ] Tests written AND passing (unit/integration/e2e per risk); coverage of AC incl. negatives
[ ] Code reviewed and approved (>=1 reviewer)
[ ] CI green — build, lint, type-check, tests all pass
[ ] NFRs met — perf budget, security/authz, a11y, observability in place
[ ] Docs/changelog/API docs updated
[ ] Merged to main and deployed (to the target env)
[ ] Verified against every AC (by someone other than author where possible)
[ ] No known regressions; no new critical/high bugs; flags/config set
[ ] Product owner accepts (demo/sign-off)
```
- DoD applies to EVERY story identically — it's the quality floor. If a box can't be checked, the story isn't done; carry it, don't fake it.

## Ready vs Done — quick contrast
- Ready = "we understand it well enough to build it right." Done = "it's built right and shippable."
- Ready is about **clarity + dependencies**; Done is about **quality + completeness**.
- A story can be Done technically but not Done by AC — the AC check is the arbiter, not the dev's opinion.

## Per-team customization
- Start from a template, then tune to the team's reality (deploy pipeline, compliance, platforms). A mobile team's DoD includes store-build; a data team's includes backfill verified.
- Keep it **short and real** — 6–10 items each. A 30-item checklist gets skipped. Every item must be one the team actually enforces.
- Post it where work happens (board column definition, PR template, story template). Revisit in retros; prune items that never fail and add ones that keep biting.

## INVEST feeds DoR
- A story that fails **INVEST** usually fails DoR: not **I**ndependent -> unresolved dependency; not **S**mall/**E**stimable -> can't size; not **T**estable -> AC aren't objective. Use INVEST as the pre-check before running the DoR list.
- DoR is where "this is really an epic" gets caught: if it can't be sized under a sprint, it's not Ready — split at refinement, don't pull-and-hope.

## Layered DoD (story / sprint / release)
- **Story DoD**: coded, tested, reviewed, merged, AC-verified. Per item.
- **Sprint/increment DoD**: integrated, regression suite green, increment demoable/deployable, sprint goal met.
- **Release DoD**: perf/load tested, security review, docs + runbook, feature flags/rollout plan, monitoring/alerts live, rollback tested, stakeholder sign-off, compliance.
- Not everything must be done every story — some quality gates (load test, pen test) live at the release layer. Make the layering explicit so nothing falls between cracks.

## DoD for bug fixes vs features
- **Feature DoD**: full checklist above (AC, docs, demo).
- **Bug-fix DoD**: reproduce first; **regression test that fails before, passes after** (proves the fix + prevents recurrence); root cause noted; check for sibling occurrences of the same bug; verify in the env it was reported.
```
Bug DoD:
[ ] Reproduced; root cause identified
[ ] Failing test added that reproduces the bug
[ ] Fix makes that test pass; existing tests still green
[ ] Same bug class checked elsewhere in code
[ ] Verified in reporting environment; ticket links commit
```
- **Tech-debt/enabler DoD**: define "done" as a measurable outcome (e.g. "p95 < 200ms", "0 deprecation warnings", "coverage on module X >= 80%") — don't leave it vague or it's never done.

## Cost of pulling not-ready stories
- Mid-sprint clarification stalls: dev blocks waiting on PO/design -> context switch -> velocity churn.
- Rework: built the wrong thing because AC were fuzzy; discovered in review/demo.
- Scope creep: undefined edges get "figured out" ad hoc, inconsistently.
- Estimate blows up: hidden unknown surfaces after commitment; sprint goal missed.
- Carry-over: not-ready stories dominate spillover. DoR is cheap insurance against all of this.
- The unit economics: minutes of refinement to make a story Ready vs hours-to-days of blocked dev time + rework when it isn't. DoR is the cheapest quality gate you have — it fails work before it costs anything to build.
- Second-order cost: a stalled story blocks its dependents and inflates WIP, so one not-Ready pull degrades the whole sprint's flow, not just that card.

## Applying the gates in practice
- **DoR at refinement, not planning**: refinement clears stories to Ready; planning just pulls from the Ready pool. If planning turns into clarifying sessions, refinement is failing.
- **Who checks**: DoR checked by team + PO during refinement; DoD checked by reviewer/QA/PO at story close. Neither is the author self-certifying alone.
- **Board wiring**: encode DoR as the entry criteria for the "To Do"/"Ready" column and DoD as the exit criteria for "Done". A card can't move columns until its gate passes.
- **WIP + carry-over signal**: chronic spillover usually traces to not-Ready pulls (DoR gap) or "done-ish" work reopened (DoD gap). Use retro to find which.
- **Don't gold-plate the gates**: DoR/DoD exist to prevent specific pains the team has felt. Every item should map to a real past failure; if it never fires, cut it.

## Ready/Done for spikes and enablers
- **Spike DoR**: timeboxed, has a specific question to answer, has a named decision it will unblock. Not "research payments" — "decide if PSP supports partial refunds; output: yes/no + contract."
- **Spike DoD**: the question is answered and the **outcome is written back** (decision, contract, updated estimate) onto the dependent story. Code from a spike is throwaway; the decision is the deliverable.
- **Enabler/tech-debt DoD**: a measurable target, not "improved". e.g. "build time < 90s", "no P1 deprecations", "module X coverage >= 80%". Vague = never done.

## Making DoD machine-checkable
- Automate what you can so DoD isn't a memory test: CI enforces tests-pass, lint, type-check, coverage threshold, no-merge-without-review (branch protection), build succeeds.
- PR template with DoD checkboxes; require them ticked. Status checks block merge.
- Automated a11y/perf budgets (Lighthouse CI), security scan (SAST/deps), deploy-verify smoke test.
- Reserve human judgment for what can't be automated: AC-met, UX quality, docs adequacy. Let machines own the mechanical gates.

## Pitfalls -> Fix
- **DoR as bureaucracy**: 20-item gate blocks everything, refinement becomes theater. Fix: trim to the few items that actually predict stalls; DoR serves the team, not vice versa.
- **DoD ignored under pressure**: "ship now, test later" at deadline. Fix: make DoD non-negotiable + machine-enforced (CI blocks); "later" tests rarely get written. If you must cut, cut scope, not DoD.
- **"Done" != "done done"**: dev-complete counted as done; QA/deploy trails into next sprint. Fix: DoD includes tested + merged + deployed + AC-verified; no partial credit.
- **Untestable AC passing DoR**: "works well", "user-friendly" slip the gate. Fix: DoR requires objective pass/fail AC; reject subjective criteria at refinement.
- **No DoD for tech debt/spikes**: open-ended, never finish. Fix: define measurable completion (metric/threshold/decision-doc) up front.
- **DoR/DoD written once, never revisited**: drifts from reality, gets ignored. Fix: review in retro; prune dead items, add ones that keep biting.
- **Same DoD forced on bugs and features**: bug fix waits on "update user docs" it doesn't need. Fix: a lean bug-fix DoD (repro + regression test + root cause) distinct from feature DoD.
- **Gate with no teeth**: checklist exists but nobody enforces it. Fix: wire into board columns / PR template / branch protection so it's structurally required, not optional.
- **Ready stories go stale**: refined months ago, context changed. Fix: refine near the sprint (last responsible moment); re-check DoR at planning.
- **DoR used to gold-plate**: demanding full design + spec before ANY work, killing agility. Fix: Ready = enough to start safely, not everything answered; some detail emerges in the doing.
- **Skipping DoR on "small" stories**: "it's trivial" -> hidden dependency stalls it. Fix: quick DoR check on everything; small stories hide big unknowns.
- **Regression bug reappears**: fixed without a test. Fix: bug DoD mandates a failing-first regression test — the fix isn't done without it.
- **Definition varies by person**: each dev's "done" differs. Fix: single written team DoD is the arbiter, not individual judgment.
- **AC verified only by author**: confirmation bias passes broken work. Fix: DoD requires independent verification (QA/PO/peer) against AC.
