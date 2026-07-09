# Requirements Engineering
## Functional vs non-functional
- **Functional (FR)**: what the system does — inputs, behavior, outputs (e.g., "system emails a receipt on payment").
- **Non-functional (NFR / quality attributes)**: how well it does it. Categories:
  - **Performance**: latency, throughput, capacity (e.g., "p95 search < 300 ms at 1k rps").
  - **Security**: authN/authZ, encryption, audit, least privilege, compliance (GDPR/PCI).
  - **Usability/accessibility**: task time, error rate, WCAG 2.1 AA.
  - **Reliability/availability**: uptime SLA (99.9%), MTBF, RPO/RTO, graceful degradation.
  - **Scalability, maintainability, portability, compatibility, observability**.
- **Constraints**: fixed non-negotiables (tech stack, budget, regulation, deadline). NFRs are often where projects fail late; capture early and make each measurable.
## RE process
1. **Elicitation**: interviews, workshops, observation, document analysis, prototyping, surveys.
2. **Analysis**: model, decompose, resolve conflicts, detect gaps/overlaps, feasibility.
3. **Specification**: document precisely (SRS, user stories, use cases, models).
4. **Validation**: confirm requirements are correct/complete/agreed with stakeholders (reviews, walkthroughs, prototypes, acceptance criteria).
- **Verification** (built it right) vs **validation** (built the right thing). Iterative, not strictly linear.
## Specifying well
- Each requirement: **atomic, unambiguous, verifiable, feasible, necessary, traceable, consistent, prioritized** (IEEE 830 / ISO 29148 quality set).
- Use "shall" for mandatory; avoid "should/may" ambiguity in binding specs. One requirement per statement (no "and").
- State rationale + source for each; attach fit criteria (measurable pass condition) to NFRs.
## Prioritization
- **MoSCoW**: Must (non-negotiable for release), Should (important, not vital), Could (nice-to-have), Won't (this time). Cap Musts at ~60% of effort.
- **Kano**: Basic/threshold (dissatisfiers if absent), Performance/linear (more=better), Excitement/delighters (unexpected). Basics first.
- **WSJF** (SAFe): Cost of Delay / Job Size; rank highest first. Cost of Delay = user value + time criticality + risk-reduction/opportunity.
- **Value vs effort** 2x2, **100-dollar test** (allocate fixed budget), **relative weighting**.
## Traceability
- Link forward and backward: business objective -> requirement -> design -> code -> test case. Enables impact analysis and coverage checks.
- **Requirements Traceability Matrix (RTM)** rows = requirements, columns = source, priority, design ref, test case, status.

```
Req ID | Requirement          | Source     | Prio | Test  | Status
FR-12  | Email receipt on pay | Interview3 | Must | TC-08 | Verified
```
## Managing change
- Baseline requirements; route changes through **change control** (impact analysis on scope/cost/schedule/other reqs, then approve/reject/defer).
- Version and status each requirement (proposed/approved/implemented/verified/rejected). RTM makes ripple effects visible.
## Specification vehicles
- **SRS / requirements document** (plan-driven, IEEE 830 / ISO/IEC/IEEE 29148): structured, baselined, formally reviewed.
- **User stories + acceptance criteria** (agile): lightweight, conversation-anchored, refined continuously.
- **Use cases**: goal-oriented actor-system interactions with main and alternate flows.
- **Models**: BPMN, state machines, data models, decision tables — a picture removes ambiguity text can't.
- Match the vehicle to volatility and compliance: regulated/fixed-scope favors SRS; volatile/discovery favors stories.
## Modeling to sharpen requirements
- **Context/scope diagram**: system boundary, external actors, data crossing it — defines what's in vs out.
- **Data model / glossary / data dictionary**: one agreed meaning per term; kills synonym/homonym ambiguity.
- **Decision tables**: exhaustively pair conditions to actions; expose missing combinations.
- **State transition models**: legal entity states and transitions; catch illegal/undefined transitions.
## Validation vs verification techniques
- **Reviews/inspections/walkthroughs**: peers and stakeholders read against a checklist.
- **Prototyping**: elicit reactions to a concrete artifact before committing to build.
- **Acceptance criteria / test cases**: pre-agree the measurable pass condition; a requirement with no test is not verifiable.
- **Model checking / prototyping / simulation** for complex logic.
## Quality of a good requirement set (ISO 29148)
- Individually: complete, unambiguous, verifiable, feasible, necessary, singular, traceable, implementation-free.
- As a set: consistent (no conflicts), complete (no gaps), non-redundant, prioritized, and bounded (in-scope only).
## NFR elicitation checklist
- For each capability ask: how fast (performance/latency/throughput), how many (capacity/scale), how safe (security/privacy/compliance), how available (uptime/recovery), how easy (usability/accessibility), how maintainable, how observable, under what constraints (legal, tech, budget).
- Attach a **fit criterion** to every NFR: a measurable pass condition with units and a percentile ("p95 < 300 ms", "99.9% monthly uptime", "WCAG 2.1 AA"). "Fast"/"secure" without numbers is untestable.
- NFRs are often architectural drivers — surface them early because they're expensive to retrofit.
## Ambiguity smells (scan for these)
- Vague adjectives/adverbs: fast, easy, robust, approximately, minimal, user-friendly.
- Open-ended lists: "etc.", "and so on", "including but not limited to".
- Ambiguous quantifiers: "all", "some", "usually", "as appropriate".
- Undefined pronouns/passive voice hiding the actor: "it shall be sent" — by what, to whom, when?
- Fix each by naming the actor, quantifying the threshold, and closing the list.
## Pitfalls -> Fix
- **Ambiguity**: "fast", "user-friendly", "etc.", "and/or", passive voice hiding the actor. Fix: quantify, name the actor, one interpretation only.
- **Missing NFRs**: only functional captured; performance/security emerge in prod. Fix: run an NFR checklist per feature; attach fit criteria.
- **Incompleteness**: undefined error handling, empty/boundary states, "what if it fails". Fix: elicit exceptions and edge cases explicitly; use checklists.
- **Gold-plating / scope creep**: unrequested features; requirements without a source. Fix: every requirement traces to a business need; use MoSCoW to cut.
- **Untraceable requirements**: can't tell why it exists or if tested. Fix: maintain an RTM from day one.
- **Solution-as-requirement**: prescribes a design instead of a need. Fix: state the problem/outcome; keep design open.
- **Conflicting requirements**: two stakeholders, incompatible asks. Fix: surface in analysis; negotiate/prioritize, record the decision.
- **Un-prioritized backlog**: everything "high". Fix: force-rank with MoSCoW/WSJF; if all are Must, none are.
- **No validation**: sign-off without stakeholder confirmation. Fix: review/prototype/acceptance-test against real needs before build.
- **Uncontrolled change**: verbal scope changes. Fix: change control with impact analysis; re-baseline.
- **Compound requirements**: multiple needs in one line ("and"). Fix: split to atomic statements so each is independently testable.
