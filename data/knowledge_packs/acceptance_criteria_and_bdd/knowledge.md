# Acceptance Criteria and BDD
## What AC are
- Conditions a story must meet to be accepted — the pass/fail boundary. Written before dev starts; owned by PO/BA, confirmed by the team.
- Scope one story; if AC balloon (>~6), the story is too big — split it.
## Two AC styles
- **Rule-based (checklist)**: terse verifiable statements. Good for CRUD, validation, constraints.

```
- Password must be >= 12 chars.
- Lockout after 5 failed attempts within 10 min.
- Reset link expires after 60 min.
```
- **Scenario-based (Gherkin / Given-When-Then)**: behavior in context. Good for workflows, state-dependent behavior.

```
Scenario: Withdraw within balance
  Given my account balance is $100
  When I withdraw $40
  Then my balance should be $60
  And I should receive $40 in cash
```
- Given = precondition/context; When = action/event (one trigger); Then = observable outcome. `And`/`But` extend any clause. `Scenario Outline` + `Examples` table for data-driven variants.
## BDD & the Three Amigos
- **BDD** (Dan North): specify behavior in ubiquitous language, examples become executable specs (Cucumber/SpecFlow/Behave -> living documentation).
- **Three Amigos**: business (PO/BA — what/why), development (how), testing (edge/negative cases) review each story together before build. Shared understanding, fewer defects.
- **Outside-in**: start from user-observable behavior, drive implementation inward.
## Example Mapping (Matt Wynne)
- 25-min structured conversation using colored cards: yellow = **story**, blue = **rules**, green = **examples** (illustrate rules), red = **questions/unknowns**.
- Outcome: rules become AC groups, examples become scenarios, red cards flag what to resolve before the story is Ready. Too many reds = not ready; too many rules = split.
## Writing testable AC
- Each AC must be **unambiguous, verifiable, atomic**, and independent of implementation ("what", not "how").
- Include **happy path + negative + edge/boundary** cases: empty, max, min, zero, invalid input, timeout, permission-denied, concurrent.
- Prefer concrete values over adjectives: "responds in < 500 ms at p95" not "fast".
## AC vs Definition of Done
- **AC**: story-specific — did we build the right thing for this story.
- **DoD**: universal checklist across all stories — coded, unit-tested, reviewed, integrated, docs updated, deployed. A story is complete only when AC met AND DoD satisfied.
- **Definition of Ready** is the entry gate; DoD is the exit gate; AC sit inside the story defining its behavior.
## From AC to automated checks
- Gherkin scenarios map 1:1 to step definitions (glue code) in Cucumber/SpecFlow/Behave/pytest-bdd. Steps drive the system and assert the Then.
- Passing scenarios become **living documentation** — the spec stays true because it executes in CI. Rule-based AC map to unit/integration assertions.
- Keep scenarios declarative and stable; put UI selectors/data in step code, not in the feature file.
## Structuring scenarios
- **Background**: shared Given for all scenarios in a feature (setup once, DRY).
- **Scenario Outline + Examples**: one behavior, many data rows — replaces near-duplicate scenarios.
- One feature file per capability; a handful of scenarios each. Tag (`@smoke`, `@regression`) for selective runs.

```
Scenario Outline: Discount tiers
  Given a cart total of <total>
  When I apply the loyalty discount
  Then I pay <final>
  Examples:
    | total | final |
    |  50   |  50   |
    | 100   |  90   |
    | 200   | 170   |
```
## Coverage thinking
- Per rule, enumerate: valid representative, boundary (min/max/off-by-one), invalid, empty/null, and error/timeout. **Equivalence partitioning** + **boundary-value analysis** keep the scenario set small but complete.
- Decision tables help when several conditions combine — one scenario per meaningful rule row.
## Roles & timing
- **PO/BA** drafts AC and owns the "what/why"; **dev** owns the "how"; **QA/tester** stresses edges and negatives. All three (Three Amigos) agree AC before the story enters the sprint — part of Definition of Ready.
- AC precede coding: they shape the tests (TDD/BDD) and the demo. Retrofitting AC after build defeats the purpose.
## Good vs bad AC (contrast)
- Bad: "The system should handle errors gracefully." Untestable, vague.
- Better: "Given the payment gateway times out, when I submit an order, then I see 'Payment could not be processed' and no charge is recorded."
- Bad: "Search is fast." Better: "Given 1M products, when I search, then results return in < 500 ms at p95."
- Bad: "Validate the form." Better: enumerate each field's rule as an atomic checklist item with the exact message shown.
## SBE / living documentation loop
- **Specification by Example** (Gojko Adzic): derive scenarios from concrete real examples, refine to key examples, automate them, evolve as living docs. The examples are the requirement, the test, and the documentation at once.
## Pitfalls -> Fix
- **Ambiguous wording**: "user-friendly", "fast", "handle errors gracefully". Fix: replace with measurable criteria and specific values.
- **Untestable AC**: no observable outcome to check. Fix: rewrite so a tester can produce a clear pass/fail; every Then is observable.
- **Implementation leakage**: "insert a row into users_table", "call the /v2 endpoint". Fix: describe behavior, not internals; keep AC design-agnostic.
- **Happy-path only**: no negatives/edges. Fix: add scenarios for invalid, empty, boundary, and error conditions (three amigos' tester surfaces these).
- **Gold-plating**: AC add behavior beyond the story's need. Fix: trace each AC to the story's benefit; drop extras or spin off a new story.
- **Multiple triggers in one scenario**: several `When`s. Fix: one action per scenario; split into separate scenarios.
- **Imperative/UI-scripted Gherkin**: "When I click the 3rd button, type X, press Enter". Fix: declarative intent ("When I submit the order") — resilient to UI change.
- **AC written after coding**: retrofitted to what was built. Fix: define AC before development (part of DoR).
- **Compound/branching Then**: outcome depends on hidden conditions. Fix: split into scenarios per branch or use Scenario Outline.
- **Conflating AC with DoD**: putting "code reviewed" in a story's AC. Fix: keep universal quality gates in DoD; keep behavior in AC.
- **Vague quantities**: "many items", "large file". Fix: state exact thresholds and units.
- **Scenario coupling**: one scenario depends on another's leftover state. Fix: each scenario self-contained via its Given.
