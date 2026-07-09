# SDLC Models
## Phases (universal)
- Requirements (elicit/spec + acceptance criteria) -> Design (architecture, data, interfaces) -> Implementation (code + unit tests) -> Testing (integration, system, UAT) -> Deployment (release to prod) -> Maintenance (bug fix, patch, evolve). Maintenance is ~60-80% of total lifecycle cost.
- Verification = "built right" (matches spec). Validation = "built the right thing" (meets user need).

## Waterfall
- Sequential, phase-gated: each phase completes + signs off before next starts. Heavy up-front docs (SRS, design spec).
- Strengths: predictable, auditable, fixed scope/contract, clear milestones. Fits regulated/safety-critical + stable, well-understood requirements.
- Weaknesses: no working software until late; expensive late changes; integration risk deferred to the end; poor fit for volatile requirements.
- When: requirements frozen, compliance-driven, fixed-bid contracts.

## V-Model
- Waterfall bent into a V: each dev phase (left) pairs with a test level (right). Requirements<->Acceptance test, System design<->System test, Architecture<->Integration test, Module design<->Unit test.
- Strength: test planning starts early (write test level's plan when its design phase runs). Same rigidity weakness as Waterfall.
- When: high-reliability/embedded, medical, avionics.

## Iterative / Incremental
- Iterative: refine the whole through repeated cycles. Incremental: deliver in slices, each adding usable function.
- Strengths: early partial delivery, feedback per cycle, risk spread. Weakness: needs good architecture up front or accrues rework.

## Spiral (risk-driven)
- Boehm. Each loop = 4 quadrants: (1) determine objectives/constraints, (2) identify + evaluate risks, prototype, (3) develop + verify, (4) plan next iteration. Risk analysis every loop drives whether to proceed.
- Strengths: explicit risk management, prototyping, good for large/expensive/unclear projects. Weaknesses: costly, needs risk-assessment expertise, complex to manage.
- When: large-budget, high-risk, novel systems.

## Agile
- Iterative + incremental with short cycles (1-4 wk), working software as primary progress measure, embrace change. Manifesto values: individuals+interactions > processes+tools; working software > docs; customer collaboration > contract negotiation; responding to change > following a plan (right items matter, but left valued more).
- Strengths: fast feedback, adaptable scope, early value, continuous stakeholder involvement. Weaknesses: harder to fix-bid/predict end date, needs disciplined engineering + available customer, scaling overhead.
- Frameworks: Scrum, Kanban, XP (extreme programming: TDD, pair programming, CI, small releases).
- When: evolving requirements, product development, uncertain domains.

## RUP (Rational Unified Process)
- Iterative, use-case-driven, architecture-centric. 4 phases: Inception (scope, business case), Elaboration (baseline architecture, retire top risks), Construction (build the bulk), Transition (beta, deploy, handover) — each with 1+ iterations + a milestone. Disciplines (business modeling, requirements, analysis/design, implementation, test, deployment, config/change mgmt, project mgmt, environment) run across phases with varying intensity. Heavier/tailorable; predecessor influence on Agile + Unified Process.

## Prototyping models
- Throwaway prototype: build to clarify requirements, then discard. Evolutionary prototype: refine the prototype into the product. Reduces requirement risk; danger is shipping a throwaway prototype as production.

## Agile frameworks compared
- Scrum: timeboxed sprints, roles, ceremonies (planning/review/retro). Kanban: continuous flow, WIP limits, no timebox. XP: engineering practices — TDD, pair programming, continuous integration, refactoring, small releases, collective ownership. Lean/SAFe/LeSS: scaling + flow. Most teams blend (e.g. Scrum + XP practices).

## Choosing a model
- Stable requirements + compliance -> Waterfall/V-model.
- High project risk/novelty + budget -> Spiral.
- Evolving requirements + fast delivery -> Agile.
- Large enterprise, need traceability + iteration -> RUP/iterative.
- Levers: requirement volatility, risk, team size/distribution, regulatory needs, customer availability, delivery-cadence needs.

## Cost of change
- Waterfall/V: cost of a change rises steeply the later it is found (defect found in prod can be 10-100x cheaper to fix at requirements). Agile flattens this curve via short cycles + automated tests + CI.

## Common misconceptions
- "Agile = no documentation": Agile keeps just-enough, living docs, not zero docs.
- "Agile = no architecture/design": emergent design still needs deliberate architecture (esp. at scale); "no design" causes debt.
- "Waterfall is always wrong": for stable, regulated, fixed-scope work it is a rational choice.
- "Iterative = ad hoc": iterations are planned + time-boxed with goals, not improvised.
- "Spiral = many prototypes": Spiral is defined by per-loop risk analysis, not by prototyping alone.
- "V-model tests only at the end": test planning starts alongside each design phase, execution flows bottom-up.
- "One model fits the whole org": model choice is per-project; hybrids are valid when intentional.

## Pitfalls -> Fix
- **"Agile means no planning/no docs"**: false. Agile plans continuously (release + sprint + daily) and keeps just-enough docs. Fix: treat backlog + estimates + DoD as the plan; document decisions that outlive a sprint.
- **Waterfall by default for volatile requirements**: forces guessing + late discovery. Fix: pick model from requirement volatility + risk, not habit.
- **Big-bang integration**: deferring all integration to the end hides interface defects. Fix: continuous integration or incremental integration each cycle.
- **Spiral without real risk analysis**: becomes expensive iterative with ceremony. Fix: each loop must produce ranked risks + mitigations, or don't use Spiral.
- **Skipping validation, only verifying**: you build exactly the wrong thing correctly. Fix: validate against user need (UAT, demos) as well as spec.
- **Treating "Agile" as a license to skip testing/design**: causes technical-debt spiral. Fix: XP-style engineering discipline (tests, refactoring, CI) is mandatory in Agile.
- **Phase-gate sign-offs used as blame gates**: teams over-document to cover themselves. Fix: gates verify readiness, not assign blame.
- **One-size-fits-all across a portfolio**: different products need different models. Fix: tailor per project; hybrids (e.g. Water-Scrum-fall) are legitimate if deliberate.
- **Maintenance under-resourced**: it dominates lifecycle cost yet is ignored in plans. Fix: budget + staff maintenance from day one.
