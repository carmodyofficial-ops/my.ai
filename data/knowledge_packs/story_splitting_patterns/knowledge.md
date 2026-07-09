# Story Splitting Patterns
## Why split
- **Fit a unit of delivery**: one iteration/sprint, or one agent session — a story too big to finish in one pass loses coherence and stalls.
- **Faster feedback**: smaller slices ship sooner, get demoed/validated sooner, surface wrong assumptions early.
- **Reduce risk**: isolate the uncertain/complex bit; deliver the certain value now, defer the rest.
- **Flow & throughput**: many small items > few big ones (Little's law — smaller batch = shorter cycle time, less WIP).
- **Estimability**: small slices size accurately; a 13+ pointer hides unknowns.
## Right-size SIGNALS (split when)
- **>~5–6 acceptance criteria** on one card.
- **"and" / "or" in the title**: "search AND filter AND export" — each conjunct is usually a seam.
- **Multiple actors/roles** in one story (admin + shopper + guest).
- **Estimate > iteration** (13+ points, or "more than N days").
- **Multiple CRUD verbs**, multiple data types, or multiple UI surfaces named.
- **Vague verbs**: "manage", "handle", "support" — hide several behaviors.
- **Can't demo it in one sitting** / can't write a crisp done check.
## SPIDR (Mike Cohn — 5 quick seams)
- **S — Spike**: research unknowns first as a separate time-boxed item, then split the now-understood story. Spike is throwaway learning, not shippable value.
- **P — Path**: split the flows through the story. Happy path first; alternate/error paths later.
- **I — Interface**: split by device, browser, input method, or API-then-UI.
- **D — Data**: split by data type/subset/source — one format now, others later.
- **R — Rules**: split by business-rule variation — simplest rule first, exceptions later.
```
Story: "User pays for order"
S: spike payment-gateway API (1 day, throwaway)
P: happy path (valid card) | declined card | timeout/retry
I: pay via saved card | new card | Apple Pay
D: USD orders | multi-currency | gift cards
R: no tax | US sales tax | EU VAT | tax-exempt
```
## Full pattern catalog
- **By workflow steps**: a multi-step process -> one story per step. "Submit expense" -> enter -> attach receipt -> approve -> reimburse.
- **By business-rule variation** (SPIDR-R): core rule now, each exception a story. "Apply discount" -> flat % | tiered | coupon | loyalty.
- **By happy / edge / error path** (SPIDR-P): ship the golden path, add negative/empty/edge cases as follow-ups (still write the AC for them).
- **By CRUD operation**: Create | Read | Update | Delete as separate stories — Read/Create often ship first, Delete last.
- **By data type / format / range** (SPIDR-D): CSV import now, XLSX later; single record then bulk.
- **By input / interface** (SPIDR-I): **API first, UI second** — deliver the endpoint, then the screen. Or one browser/device then others.
- **By operations (defer non-functional)**: build functional behavior; split out performance, i18n, a11y, hardening as separate stories with their own AC (don't lose them).
- **By effort / capacity**: cut a slice sized to what fits, leave the remainder as a sibling story.
- **Simple-then-complex**: implement the trivial case end-to-end; enrich later.
- **Zero / one / many**: handle the empty case, then single, then collection — three natural slices.
- **Walking skeleton first**: thinnest possible end-to-end path (real DB->real API->real UI, hardcoded/stubbed logic) to prove the architecture; then thicken each part with real stories.
## Epic -> feature -> story -> slice
- **Epic**: multi-release container, not estimable ("Checkout").
- **Feature**: deliverable chunk of an epic, still > one iteration ("Guest checkout").
- **Story**: one thin vertical slice, fits an iteration, own AC ("guest enters shipping address").
- **Slice for an agent**: a story sized to one coherent agent session — often == a story, sometimes one story = a few agent sub-tasks. Splitting patterns apply at every level; the seams (SPIDR/workflow/rules) are the same.
## Vertical vs horizontal
- **Vertical (thin end-to-end)** = CORRECT: each slice cuts through all layers (DB -> service -> API -> UI) and is demoable/valuable on its own.
- **Horizontal (by layer)** = ANTI-PATTERN: "build the schema", "build the service", "build the UI" — none ships user value alone; integration risk piles up at the end.
```
BAD (horizontal):
  Story A: create users DB table
  Story B: build user-service CRUD
  Story C: build user admin UI
GOOD (vertical):
  Story A: admin creates a user (table+service+UI, one field set)
  Story B: admin deactivates a user
  Story C: admin bulk-imports users from CSV
```
## Worked BEFORE -> AFTER splits
```
BEFORE: "As a user I want to search, filter, and sort products"  (13 pts, 3 verbs)
AFTER:
  1. keyword search returns matching products (happy path)
  2. filter results by category
  3. sort results by price / relevance
  (SPIDR seam: the "and" in the title)
```
```
BEFORE: "Import contacts"  (CSV, vCard, Google, 8 AC)
AFTER (by data source/type, SPIDR-D):
  1. import from CSV (map columns, dedupe)  <- ship first
  2. import from vCard file
  3. import from Google Contacts (OAuth)  <- carries a spike
```
```
BEFORE: "Checkout with payment"  (huge)
AFTER (walking skeleton + paths):
  0. walking skeleton: place a $0 order end-to-end (stub payment)
  1. pay with valid card (happy path, USD)
  2. handle declined card (SPIDR-P)
  3. add sales tax by region (SPIDR-R)
  4. email receipt (workflow step)
```
## Finding the seam (how to choose a pattern)
- Read the AC list — **each cluster of AC is a candidate slice**. 12 AC that group 4/4/4 -> 3 stories.
- Scan the title for **"and"/"or"/commas** -> conjunction boundaries.
- List the **flows** (happy/alt/error) -> SPIDR-P seams.
- List the **rules/variations** (regions, tiers, plan types) -> SPIDR-R seams.
- List the **data types/sources** -> SPIDR-D seams.
- Count **actors** -> often one story per actor.
- If nothing obvious: build the **walking skeleton**, then every "thicken" is a slice.
- Try 2–3 seams, pick the one giving the most **independent, valuable, similar-sized** slices (SPIDR order is a fast checklist, not a ranking).
## After splitting — re-check INVEST
- **I**ndependent: can each ship without the others? If not, re-cut.
- **V**aluable: each slice demoable to a user/stakeholder (not a task).
- **E**stimable / **S**mall: each fits the iteration/session with margin.
- **T**estable: each has crisp AC / a done check.
- If a slice fails INVEST, the seam was wrong — try another pattern.
## Sequencing & sizing the slices
- **Order by value + risk + learning**: ship the slice that de-risks the most or proves the architecture first (walking skeleton, riskiest rule, or highest-value path).
- Slices needn't be equal size, but wildly uneven slices hint at a bad seam.
- **Deferred slices go to the backlog with their AC** immediately — a split is a promise to do the rest, not a license to drop it.
- Combine patterns freely: split by workflow step, then split a heavy step by rules.
## More BEFORE -> AFTER splits
```
BEFORE: "Admin manages users"  (vague verb, all CRUD)
AFTER (by CRUD + simple-first):
  1. admin views user list (Read)          <- ship first
  2. admin creates a user (Create)
  3. admin edits a user (Update)
  4. admin deactivates a user (soft Delete)
```
```
BEFORE: "Generate monthly report"  (formats + delivery + scheduling)
AFTER (data type / interface / operations):
  1. generate report on demand, HTML in-browser (happy path)
  2. export the report as PDF (SPIDR-D)
  3. email the report to the owner (workflow step)
  4. schedule it monthly (defer — its own slice)
  5. handle empty-data month (zero/one/many)
```
```
BEFORE: "Onboarding wizard (5 steps)"
AFTER (by workflow step, walking skeleton first):
  0. skeleton: click through 5 empty steps, save nothing
  1. step 1 collects & persists profile
  2. step 2 collects preferences
  ... one slice per step, each end-to-end
```
## When NOT to split
- Slice would be **below the value floor** — no independently demoable user value (that's a task, keep it in the parent).
- Story **already fits** the iteration/session and has a clean done check.
- Splitting would **create tight sequential dependencies** (A useless without B,C) — INVEST-Independent broken; keep together or re-slice differently.
- **Cohesive rule set** where separating rules ships something misleading/unsafe (e.g., auth checks — don't ship the half without the deny path).
- Cost of coordinating the split > cost of doing it whole.
## Pitfalls -> Fix
- **Splitting by component/layer**: "backend story" + "frontend story". Fix: slice vertically; each story spans all layers, thin but complete.
- **Slices with no user value**: "set up the config module". Fix: attach to a demoable capability or keep as a task under a value-bearing story.
- **Over-splitting into tasks**: 1-hour "stories" that individually mean nothing. Fix: a story is the smallest thing a user/stakeholder cares about; sub-steps are tasks, not stories.
- **Splits that can't ship independently**: story 2 hard-depends on stories 3–5. Fix: re-cut along a seam that yields independent value (walking skeleton, then thicken), or sequence explicitly and merge if truly inseparable.
- **Spike that never ends**: open-ended research with no deliverable. Fix: time-box it, state the question it answers and the decision it unblocks; its output is a decision, not code.
- **Golden-path-only, edges dropped**: split happy path but never write the error/empty stories. Fix: capture edge/error slices as backlog items with AC the moment you split them — a seam, not a delete.
- **Fake vertical**: "UI slice" that stubs the whole backend forever. Fix: walking skeleton must touch real layers end-to-end; stubs are temporary, replaced by later slices.
- **Splitting to hit a point target, not value**: cutting to make numbers. Fix: split along natural behavioral seams (SPIDR / workflow / rules); size follows.
- **Losing NFRs in the split**: performance/security/a11y vanish when deferred as "operations". Fix: create the non-functional slice as its own story with measurable AC, or fold into Definition of Done.
- **"and"/"or" survived into the final card**: still compound. Fix: each conjunction is a candidate boundary; one story = one coherent behavior.
