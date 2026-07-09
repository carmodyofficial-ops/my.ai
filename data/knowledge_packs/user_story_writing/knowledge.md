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
## Epics vs features vs stories
- **Epic**: large body of work spanning sprints/releases; a container, not estimable. (e.g., "Checkout")
- **Feature**: a deliverable slice of an epic, still too big for one sprint (e.g., "Guest checkout").
- **Story**: fits in one sprint, delivers a thin vertical slice of value. **Task**: dev sub-work of a story, no standalone user value.
- Theme = grouping across epics.
## Story splitting (SPIDR + patterns)
- **SPIDR** (Mike Cohn): **S**pike (research unknowns), **P**aths (split happy vs alternate flows), **I**nterfaces (by device/browser/UI variant), **D**ata (by data type/subset), **R**ules (by business-rule variation).
- Also: by **workflow steps**, by **CRUD operation**, by **acceptance-criterion count** (>~5–6 AC = split), by **effort/simple-first** (defer complexity), by operations, by role.
- Vertical slices (thin end-to-end, DB->API->UI) over horizontal (layer-by-layer). Each split must still deliver demonstrable value.
## Personas & story mapping
- **Persona**: archetypal user with goals/context/pain (name, role, motivations). Replaces vague "user" with a real <role>.
- **Story map** (Jeff Patton): backbone of user activities left->right (narrative flow), stories stacked top->down by priority. Horizontal slices = releases/MVP. Exposes gaps a flat backlog hides.
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
## Worked split example
- Epic "Checkout" -> feature "Guest checkout" -> stories: enter shipping address; select shipping method (SPIDR-Rules by region); pay by card (happy path); handle declined card (SPIDR-Paths); email confirmation. Each is a thin vertical slice, independently demoable, sized <= 8 points.
- Rule of thumb: if a story generates the word "and" or more than ~6 acceptance criteria, look for a natural SPIDR seam and cut there.
