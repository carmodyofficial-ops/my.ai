# Business Analysis Fundamentals
## What a BA does
- Bridges business need and delivered solution: elicits, analyzes, specifies, validates, and manages requirements; facilitates decisions; does NOT own scope (sponsor) or build (dev).
- Core value: reduce ambiguity, surface hidden assumptions, prevent building the wrong thing. Deliverables are decisions and shared understanding, not documents.
## BABOK knowledge areas (IIBA)
- **Business Analysis Planning & Monitoring**: approach, stakeholder engagement, governance, information management.
- **Elicitation & Collaboration**: prepare, conduct, confirm results, communicate.
- **Requirements Life Cycle Management**: trace, maintain, prioritize, assess change, approve.
- **Strategy Analysis**: current state, future state, risk, change strategy.
- **Requirements Analysis & Design Definition (RADD)**: model, verify, validate, define architecture, define options.
- **Solution Evaluation**: measure performance, assess limitations, recommend action.
- Underlying competencies + 50+ techniques cut across all areas.
## Requirement types (BABOK)
- **Business**: goals/outcomes for the enterprise (e.g., "cut order-to-cash cycle 20%").
- **Stakeholder**: needs of a specific group (e.g., "warehouse lead needs pick lists sorted by aisle").
- **Solution**: what the system must do — split into **functional** (behavior) and **non-functional** (quality attributes).
- **Transition**: temporary, needed only to move as-is to to-be (data migration, training, cutover). Retired after go-live.
## Elicitation techniques
- **Interviews**: 1:1, structured/unstructured. Best for depth, sensitive topics. Prep questions; beware leading questions and single-viewpoint bias.
- **Workshops** (JAD): cross-functional, facilitated, fast consensus. Needs neutral facilitator + scribe; risk of dominant voices.
- **Observation** (job shadowing, active/passive): reveals what people actually do vs. what they say. Costly; Hawthorne effect.
- **Document analysis**: existing specs, forms, regs, tickets. Good starting context; docs may be stale.
- **Others**: surveys/questionnaires (scale, weak on nuance), prototyping (clarify UI, elicit reactions), focus groups, brainstorming, interface analysis, data mining.
- Triangulate: no single technique is sufficient; confirm findings back to sources.
## Strategy / gap analysis
- **As-is vs to-be**: model current state, define target state, the delta = scope of change. Gap analysis lists capabilities missing/changed/removed.
- **Solution scoping**: draw the boundary — in-scope vs out-of-scope, dependencies, assumptions, constraints. Context diagram / scope model shows external actors and data flows crossing the boundary.
- **SWOT**, **root-cause (5 Whys, fishbone/Ishikawa)**, **MOST** (Mission, Objectives, Strategy, Tactics) for alignment.
## Common BA deliverables
- Business case, stakeholder map / RACI, context diagram, process models (BPMN), use cases, requirements spec (functional + NFR), data dictionary/glossary, traceability matrix, wireframes, acceptance criteria.
- Sample RACI row:

```
Task                 | Sponsor | BA | Dev | QA
Approve requirements |    A    | R  |  C  |  I
Write acceptance crit|    C    | R  |  C  |  A
```
(R=Responsible, A=Accountable, C=Consulted, I=Informed)
## Stakeholder analysis
- **RACI** for task ownership; **power/interest grid** (manage closely / keep satisfied / keep informed / monitor) for engagement strategy.
- Identify: sponsor, end users, SMEs, regulators, ops/support, upstream/downstream system owners. Missing a stakeholder = missing requirements.
- **Onion diagram**: solution core -> system stakeholders -> business stakeholders -> wider environment; concentric rings show proximity to the solution.
- **CATWOE** (soft systems) to frame a change: Customers, Actors, Transformation, Worldview, Owner, Environmental constraints.
## Analysis techniques (cross-cutting)
- **Decision tables / decision trees**: enumerate condition-action combinations; catch missing rule branches.
- **State diagrams**: model entity lifecycle (order: draft -> placed -> shipped -> closed/cancelled) and valid transitions.
- **Data flow / entity-relationship / CRUD (data-vs-process) matrices**: verify every entity is Created/Read/Updated/Deleted by some process — orphan gaps signal missing requirements.
- **Prototyping/wireframes**: cheap, testable models to elicit reactions before build.
- **Prioritization inputs**: cost, value, risk, dependency, regulatory deadline — feed downstream MoSCoW/WSJF ranking.
## Business case & metrics
- Justify the change: problem statement, options considered, costs/benefits, risks, recommendation. Tie to **SMART** objectives (Specific, Measurable, Achievable, Relevant, Time-bound).
- Define **KPIs / success metrics** up front so Solution Evaluation can measure realized value (cycle time, error rate, NPS, cost per transaction).
- **ROI / payback / NPV** framing for the sponsor; a solution without a measurable benefit is a red flag.
## Approach: plan-driven vs adaptive
- **Plan-driven (waterfall)**: heavy up-front specification, formal sign-off, change control; suits fixed-scope/regulated work.
- **Adaptive (agile)**: just-enough, just-in-time requirements as backlog items refined continuously; BA acts as PO proxy / backlog steward.
- Most real work is hybrid; pick fidelity by risk, volatility, and compliance need.
## Elicitation workflow
- **Prepare** (define scope, pick technique, invite right stakeholders, draft questions) -> **conduct** (facilitate, listen, capture) -> **confirm** (play back findings in writing, resolve conflicts) -> **communicate** (distribute, get agreement).
- Open questions to explore need; closed questions to confirm detail. Watch for tacit knowledge experts can't articulate — observation surfaces it.
## Solution evaluation
- After delivery, measure realized value against the business case KPIs; identify solution limitations (internal: defects, usability) and enterprise limitations (process, org, adoption).
- Recommend action: adjust, retire, invest more, or accept. Closes the loop from need to outcome.
## Key artifacts glossary
- **Business case**: justification (problem, options, cost/benefit, recommendation).
- **Vision/scope doc**: goals, in/out of scope, constraints, assumptions.
- **Requirements package**: FRs, NFRs, models, glossary, traceability.
- **Transition requirements**: migration, training, cutover, decommissioning — temporary by nature.
## Pitfalls -> Fix
- **Documenting solutions, not needs**: requirements pre-baked as a chosen design ("add a dropdown"). Fix: ask "what problem does that solve?"; capture the need, let design stay negotiable.
- **Skipping current-state analysis**: to-be built on assumptions. Fix: model as-is first; quantify the pain (cycle time, error rate) as a baseline.
- **Single-source elicitation**: one loud SME defines the whole system. Fix: triangulate techniques and stakeholders; confirm results in writing.
- **No traceability**: can't tell why a requirement exists or if it's tested. Fix: link business objective -> requirement -> design -> test.
- **Analysis paralysis / big-bang spec**: months of docs before value. Fix: elicit incrementally, timebox, deliver in slices.
- **Gold-plating scope**: "while we're here" additions. Fix: every requirement traces to a business objective; no objective = defer.
- **Confusing want vs need**: stakeholders state wants; BA finds the underlying need. Fix: 5 Whys on each request.
- **Ambiguous glossary**: same term, different meanings across teams. Fix: maintain one shared glossary/data dictionary; define terms once.
- **Treating sign-off as done**: approval != validated solution. Fix: validate against business outcomes post-delivery (Solution Evaluation).
- **Ignoring non-functional needs**: only functional captured; performance/security bite later. Fix: elicit NFRs explicitly for every solution area.
