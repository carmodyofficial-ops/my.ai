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
## When to pick which style
- **Rule-based** when: outcome is a static true/false over inputs (validation, limits, formatting, permissions matrix, config). Cheaper, denser, no state narrative needed.
- **Scenario-based** when: behavior depends on **context/state/sequence** (workflows, state machines, multi-step interactions) or when the *example itself* clarifies a fuzzy rule for the Three Amigos.
- Common pattern: rule as the AC, one or two scenarios as its illustrative examples. Don't write a Gherkin scenario for every trivial field rule — a checklist row is enough.
## Declarative vs imperative steps
- **Declarative** = intent at the domain level: `When I submit the order`. Stable across UI change, reads as documentation.
- **Imperative** = mechanics: `When I click "#btn-3", type "42", press Enter`. Brittle, couples the spec to the UI, obscures intent.
- Rule: the feature file states *what*; the step definitions/glue hold the *how* (selectors, waits, data). Push all mechanics down into step code.
## One behavior per scenario
- A scenario asserts a **single** behavior: one `When` (trigger), a coherent `Then`. Multiple `When`s = you merged two tests; split them.
- Name scenarios after the behavior/outcome (`Withdraw more than balance is rejected`), not the steps.
- Keep 3–7 lines; long scenarios usually hide incidental setup that belongs in `Background` or step code.
## Tags & organization
- Tags select and annotate: `@smoke` `@regression` `@wip` `@slow` `@security`; tie to CI stages (`cucumber --tags @smoke`).
- Tags can carry hooks (e.g. `@db` triggers a DB reset in a Before hook) and link to work items (`@JIRA-123`).
- One feature per capability; a handful of scenarios each. Feature/Rule keyword groups scenarios under a shared business rule (Gherkin 6+).
## BDD & the Three Amigos
- **BDD** (Dan North): specify behavior in ubiquitous language, examples become executable specs (Cucumber/SpecFlow/Behave -> living documentation).
- **Three Amigos**: business (PO/BA — what/why), development (how), testing (edge/negative cases) review each story together before build. Shared understanding, fewer defects.
- **Outside-in**: start from user-observable behavior, drive implementation inward.
## Example Mapping (Matt Wynne)
- 25-min structured conversation using colored cards: yellow = **story**, blue = **rules**, green = **examples** (illustrate rules), red = **questions/unknowns**.
- Outcome: rules become AC groups, examples become scenarios, red cards flag what to resolve before the story is Ready. Too many reds = not ready; too many rules = split.
- Worked map (story "Apply coupon at checkout"):
```
STORY  Apply coupon at checkout
RULE   Percent coupons cap at 50% off
  EX   20% coupon on $100 -> $80
  EX   90% coupon rejected as invalid
RULE   Expired coupons are refused
  EX   coupon expired yesterday -> "This code has expired"
RULE   One coupon per order
  EX   second coupon replaces first? -> RED (product to decide)
?      stack with sale prices?  -> RED
```
- Resolve reds before the sprint; each rule becomes an AC line; each example becomes a scenario row.
## AC review checklist (before Ready)
- Every AC: atomic, observable Then, implementation-agnostic, has exact values/messages, one behavior.
- Set as a whole: happy + negative + boundary + error covered; no gold-plating; NFRs stated with thresholds; no incidental data; nothing that belongs in DoD.
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
- **pytest-bdd**: `@given/@when/@then` decorators bind step text to Python functions; `parsers.parse("I withdraw {amount:d}")` captures params; `Examples` rows become parametrized runs; fixtures share state.
- **Cucumber (JS/Ruby/Java)**: `Given(/^.../, fn)`; World object holds per-scenario state; Before/After hooks by tag.
- **Playwright**: drive the browser inside step code (`page.getByRole(...).click()`), keep locators out of the feature; or use `playwright-bdd` to run `.feature` files directly. Prefer role/text locators for resilient, declarative-aligned steps.
- Choose the **right level**: unit/service-level scenarios for logic (fast, stable); UI/e2e only for the few journeys that must be verified through the browser. Don't drive every rule through the UI.
## Full worked feature
```
@checkout
Feature: Guest checkout payment
  As a first-time buyer, I want to pay without an account
  so I can complete a one-off purchase.

  Background:
    Given a priced cart totalling $42.00

  Scenario: Successful card payment
    Given a valid credit card
    When I submit payment
    Then the order is created
    And the card is charged $42.00 exactly once
    And I see an order confirmation number

  Scenario: Card fails validation
    Given a card number that fails the Luhn check
    When I submit payment
    Then I see "Check your card number"
    And no charge is attempted

  Scenario: Payment gateway times out
    Given the payment gateway will not respond within 8s
    When I submit payment
    Then I see "Payment could not be processed, please try again"
    And no order is created
    And no charge is recorded

  Scenario Outline: Amount rounding by currency
    Given a cart total of <total>
    When I submit payment
    Then the captured amount is <charged>
    Examples:
      | total  | charged |
      | 42.005 | 42.01   |
      | 42.004 | 42.00   |
```
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
## Systematic edge/negative/error enumeration
- Run each input through a checklist: **empty/null**, **min & min-1**, **max & max+1**, **zero/negative**, **wrong type/format**, **duplicate**, **too long**, **special chars/unicode/injection**, **whitespace-only**.
- State/flow: **not-authenticated**, **not-authorized**, **already-done (idempotency)**, **concurrent edit**, **stale/expired**, **out-of-order steps**, **partial failure/rollback**.
- Dependencies: **downstream timeout**, **downstream 500**, **rate-limited**, **network drop mid-request**.
- For every happy-path scenario, ask "what's the opposite Then?" — a missing negative scenario is the most common defect source.
## AC for non-functional requirements
- Make NFRs testable with concrete thresholds and conditions, not adjectives:
  - Perf: `p95 response < 300 ms at 500 rps`. Load: `sustains 10k concurrent users, error rate < 0.1%`.
  - Security: `passwords hashed with bcrypt cost>=12; PAN never logged; auth required on all /admin routes`.
  - A11y: `all interactive elements keyboard-reachable; WCAG 2.1 AA contrast >= 4.5:1`.
  - Reliability: `retries transient 5xx 3x with backoff; idempotent on retry`.
- Attach to the relevant story's AC, or to the DoD if universal. Each NFR AC needs a measurement method (tool/query).
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
- **AC restate the title**: `Story "Export CSV" -> AC "user can export CSV"`. Fix: AC must add falsifiable detail (columns, delimiter, encoding, empty-set behavior), not echo the story.
- **Incidental detail**: hard-coded names/dates/ids that aren't the point (`Given user "Bob123" created 2019-04-02`). Fix: use meaningful, minimal data; abstract irrelevant specifics into Background or step code.
- **UI-coupled scenarios**: `Then the div "#toast" has class "green"`. Fix: assert user-observable outcome (`Then I see a success message`); keep DOM in step code.
- **Everything through the browser**: slow, flaky e2e for logic that a unit test covers. Fix: test at the lowest level that proves the behavior; reserve UI scenarios for key journeys.
- **NFR as adjective**: `"must be secure/fast/scalable"`. Fix: give a threshold, condition, and measurement method.
- **Too many red cards / rules on the story**: from Example Mapping. Fix: reds mean not Ready (resolve first); many rules mean split the story.
