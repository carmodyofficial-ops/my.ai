# User Story Writing
## Format
- `As a <role>, I want <capability>, so that <benefit>`. The "so that" is the value test — if you can't state it, question the story.
- A story is a placeholder for a conversation (Card, Conversation, Confirmation — Ron Jeffries' 3 Cs), not a spec. Detail arrives via acceptance criteria at the last responsible moment.
- **INVEST**: Independent, Negotiable, Valuable, Estimable, Small, Testable.
- Sample:

```
As a returning shopper,
I want to save items to a wishlist,
so that I can buy them later without re-searching.
AC: wishlist persists across sessions; max 100 items; remove item.
```
- The `As a / I want / so that` template is **Connextra** (2001). It is one option, not a mandate — value clarity beats template fidelity.
## INVEST, letter by letter (fail -> fix)
- **I**ndependent — `Story B: "apply coupon" blocked until Story A "cart totals" ships`. Fix: fold minimal totals into B, or sequence and label the dependency; avoid hidden ordering.
- **N**egotiable — `"...I want a red 'Save' button top-right"` bakes UI into the card. Fix: `"...I want to save my work"`; leave placement/design to the conversation.
- **V**aluable — `"As a dev I want a Redis cache"` has no user outcome. Fix: attach to the value it enables (`"...so pages load < 1s"`) or track as an enabler.
- **E**stimable — `"Improve search relevance"` is unsizable (unknown scope). Fix: spike first (SPIDR-S), then write sized stories.
- **S**mall — `"Manage my account"` spans dozens of behaviors. Fix: split to one behavior (`"change my email"`); >~6 AC = split.
- **T**estable — `"Search should feel fast"` has no pass/fail. Fix: `"results in < 500 ms at p95 for 1M products"`.
## Story formats beyond Connextra
- **Job story** (Alan Klement): `When <situation>, I want to <motivation>, so I can <expected outcome>`. Front-loads context/trigger over persona; good when the *who* is less important than the *situation*.
  - `When I'm mid-checkout and my card is declined, I want to try another card without re-entering the cart, so I can still complete the purchase.`
- **Feature injection / given-story**: derive stories backward from the business value — name the output/outcome first, then the minimal story that produces it. Avoids feature-first cargo-culting.
- **Role-feature-reason**, **five-Ws**, or a plain sentence are all fine. Rule: whichever format you use, the **why/value** must survive. If the template hides value, drop the template, not the value.
## Epics vs features vs stories
- **Epic**: large body of work spanning sprints/releases; a container, not estimable. (e.g., "Checkout")
- **Feature**: a deliverable slice of an epic, still too big for one sprint (e.g., "Guest checkout").
- **Story**: fits in one sprint, delivers a thin vertical slice of value. **Task**: dev sub-work of a story, no standalone user value.
- Theme = grouping across epics.
## The "so that" value test
- The `so that <benefit>` clause is a lie-detector. If you can't complete it without restating the *what* (`"...so that I can save to a wishlist"` — circular), the story may have no real value.
- Three value classes: **user-facing** (a person does something new), **business** (revenue/cost/risk/compliance), **enabling** (unblocks future user value). Enabling work is legitimate — label it as an enabler, don't disguise it in Connextra.
- If two stories share the *same* benefit, they may be one story or one is redundant.
## Story splitting (SPIDR + patterns)
- **SPIDR** (Mike Cohn): **S**pike (research unknowns), **P**aths (split happy vs alternate flows), **I**nterfaces (by device/browser/UI variant), **D**ata (by data type/subset), **R**ules (by business-rule variation).
- Also: by **workflow steps**, by **CRUD operation**, by **acceptance-criterion count** (>~5–6 AC = split), by **effort/simple-first** (defer complexity), by operations, by role.
- Vertical slices (thin end-to-end, DB->API->UI) over horizontal (layer-by-layer). Each split must still deliver demonstrable value.
## Personas & story mapping
- **Persona**: archetypal user with goals/context/pain (name, role, motivations, environment, skill level). Replaces vague "user" with a real `<role>`. Define ~3–5 primary personas; each often surfaces *different* stories for the same feature.
- **Anti-persona** (fraudster, abuser) helps generate negative/security stories.
- **Story map** (Jeff Patton): top **backbone** = user activities left->right in narrative/time order; **walking skeleton** = the second row, the thinnest end-to-end path that lets a user complete the journey; stories stack top->down by priority under each activity.
- **Slices** = horizontal lines across the map carving out releases/MVP. Each slice must let a user get through the whole backbone (thin), not perfect one column (deep). Exposes gaps a flat backlog hides and gives shared narrative context.
- Build the walking skeleton first, then thicken slice by slice.
## Sizing
- Relative estimation via **story points** (Fibonacci 1,2,3,5,8,13) or **t-shirt sizes**; planning poker for consensus. Points measure effort+complexity+uncertainty, not hours.
- If a story is 13+, split it. Velocity = points/sprint, used for forecasting only.
## Definition of Ready (DoR)
- Entry gate to sprint: story has clear value statement, acceptance criteria, no blocking dependencies, sized, dependencies/design known, testable.
- Distinct from **Definition of Done** (exit gate: coded, tested, reviewed, deployed, documented).
## Acceptance criteria on the card
- Each story carries a short list of AC (rule checklist or Given/When/Then) defining the pass/fail boundary. AC clarify the story; they are not the whole spec. >~5–6 AC signals a split.
- AC are the "Confirmation" leg of the 3 Cs and the basis for the demo and the tests.
## Backlog & refinement
- **Product backlog**: single ordered list of everything; the PO owns ordering by value/risk/dependency.
- **Refinement (grooming)**: ongoing session to split epics, add AC, size, and clear questions so top items meet DoR before sprint planning. Keep ~2 sprints of ready stories at the top.
- **Bugs, spikes, enablers, tech debt** also live in the backlog — not everything fits the As-a template, and that's fine.
## Writing quality checklist
- Verb-driven capability, named persona, explicit benefit, testable AC, single sprint-sized slice, no "and" compounding, no prescribed UI.
- Prefer active voice and concrete nouns; avoid "manage", "handle", "support" as the core verb — they hide real behavior.
- Good stories are **thin but complete**: a user can do something end-to-end when it's done.
## Writing for implementability (dev/agent-ready)
- A card is a placeholder for a conversation *between people*; an **implementable story** for a dev or an AI agent must additionally carry enough resolved detail to start coding without a round-trip. See `implementable_dev_stories` for the full contract.
- Minimum to be buildable: named persona + capability + value; testable AC covering happy/negative/edge; in/out-of-scope boundary; data shapes / example values; affected surface (endpoint, screen, module) named without prescribing internal design; error/empty states; NFR thresholds if relevant; dependencies/preconditions resolved (DoR met).
- Balance: enough context to remove ambiguity, not so much it dictates the *how*. Prescribe the **observable contract**, negotiate the **implementation**.
- Smell that a story is not implementable: reviewer must ask "what happens when…" and the card can't answer. Fix before sprint, not mid-build.
## Full worked example (implementable story)
```
Title: Guest checkout — pay by saved-less card (happy path)
As a first-time buyer (persona: "Rushed Rina", no account),
I want to pay for my cart with a credit card without registering,
so that I can complete a one-off purchase quickly.

In scope: single card payment, USD, cart already priced.
Out of scope: saved cards, PayPal, split payment, coupons (separate stories).

AC (Given/When/Then):
  - Given a priced cart and a valid card, when I submit payment,
    then the order is created, card charged once, and I see an order number.
  - Given an invalid card number (fails Luhn), when I submit,
    then I see "Check your card number" and no charge is attempted.
  - Given the gateway times out (>8s), when I submit,
    then I see "Payment could not be processed, try again" and no order/charge is recorded.
  - Given amount = $0.00, then submit is disabled.
Surface: POST /checkout/guest-pay; checkout page payment step.
NFR: p95 submit->confirmation < 3s; PAN never logged.
Size: 5 pts. DoR: met.
```
## Non-functional & constraints
- Capture NFRs (performance, security, accessibility) as AC on relevant stories, as their own constraint stories, or in the Definition of Done — don't lose them.
- Cross-cutting concerns (logging, i18n, audit) are easy to forget; add them to DoD so every story inherits them.
## Pitfalls -> Fix
- **Story too big (epic in disguise)**: can't finish in a sprint. Fix: split via SPIDR or workflow step; >~5 AC = split.
- **Technical story with no user value**: "Upgrade to React 18", "Add caching layer". Fix: attach to enabled user value, or track as an enabler/tech-debt item — don't force the As-a template. If purely internal, label it honestly.
- **Missing "so that" / no benefit**: cargo-cult template. Fix: state the value or challenge whether the story should exist.
- **Solution baked into the story**: "As a user I want a dropdown..." prescribes UI. Fix: capture the need ("I want to pick from valid options"); leave design negotiable.
- **Horizontal slices**: "build the DB layer" story delivers nothing demoable. Fix: slice vertically through all layers, thin but complete.
- **Acceptance criteria as the whole spec**: 30 bullet AC = it's an epic. Fix: split; AC clarify one story, they don't carry it.
- **"Golden path only"**: no error/empty/edge cases. Fix: split paths (SPIDR-P) into separate stories or add negative AC.
- **Compound story ("and")**: "search AND filter AND export". Fix: the word "and" in a title usually marks a split boundary.
- **Non-negotiable, over-detailed cards**: written like a contract up front. Fix: keep the card terse; defer detail to the conversation.
- **Estimating the un-estimable**: story too vague to size. Fix: spike first (SPIDR-S), then size.
- **INVEST-dependent stories**: story A can't ship without B,C,D. Fix: re-slice to make each independently valuable or sequence explicitly.
- **Persona-less "as a user"**: generic role hides real needs. Fix: name the persona; different personas often reveal different stories.
- **AC written after coding**: story judged by what got built. Fix: agree AC before the sprint (part of DoR).
- **Zombie backlog**: hundreds of stale stories nobody re-reads. Fix: keep the backlog lean; delete or archive low-value items; refine only the top.
- **"As a user" cop-out**: the generic role that fits everyone and no one. Fix: name a real persona; if truly all users, still state the concrete goal, not the role placeholder.
- **AC written as dev tasks**: `"create migration", "add controller method"` masquerading as acceptance criteria. Fix: AC state observable *behavior/outcome*; tasks live on the story's task list, not its AC.
- **Gold-plating**: story/AC add "nice to have" behavior beyond the stated benefit. Fix: trace each item to the `so that`; drop or spin off extras. YAGNI.
- **Everything is a P1**: no real priority order, so sequencing is arbitrary. Fix: force a single ordered list (WSJF/value-vs-effort); if all are top, none are.
- **Job-story context lost**: rewriting a job story into Connextra drops the triggering situation. Fix: keep the `When <situation>` if the trigger is the point.
## Worked split example
- Epic "Checkout" -> feature "Guest checkout" -> stories: enter shipping address; select shipping method (SPIDR-Rules by region); pay by card (happy path); handle declined card (SPIDR-Paths); email confirmation. Each is a thin vertical slice, independently demoable, sized <= 8 points.
- Rule of thumb: if a story generates the word "and" or more than ~6 acceptance criteria, look for a natural SPIDR seam and cut there.
