# Enterprise Product Management

## Vision & strategy
- Cascade: **vision** (aspirational 3-5yr end-state / why we exist) -> **strategy** (sequenced where-to-play / how-to-win choices; Playing-to-Win) -> **OKRs** -> **roadmap** -> **backlog**; each level constrains the next.
- Strategy is deliberate focus = what you say no to; product principles pre-decide recurring trade-offs. A "strategy" that funds everything is a wish list.
- Product-market fit: the strategy's target; measured by retention flattening, organic pull, and willingness to pay — not launch buzz.

## Discovery vs delivery
- Dual-track: continuous discovery (is it worth building?) runs alongside delivery (build it right); never let delivery starve discovery.
- Discovery de-risks four ways: value (will they use it?), usability (can they?), feasibility (can we build it?), viability (should the business?).
- Talk to customers weekly; opportunity-solution tree maps outcomes -> opportunities -> solutions -> experiments.
- Ship to learn: riskiest-assumption test (RAT) before MVP; a prototype that kills a bad idea is cheaper than a launched feature.

## Roadmap & prioritization
- **RICE**: score = (Reach x Impact x Confidence) / Effort. Reach in users/quarter, Impact on a fixed scale (3/2/1/0.5/0.25), Confidence as % , Effort in person-months. Forces apples-to-apples ranking.
- **Cost of Delay / WSJF** (SAFe): WSJF = Cost of Delay / job size; prioritizes what loses the most value by waiting — best for time-sensitive/dependency-heavy work.
- **MoSCoW**: Must/Should/Could/Won't — good for scope negotiation and release cuts, weak for ranking within a bucket.
- **Kano**: separates must-be (dissatisfiers), performance, and delighter features; delighters decay to expected over time.
- Roadmap as outcomes/themes, not a dated feature list; now/next/later beats a false Gantt. Tie each item to a metric it moves.
- Cap WIP; a roadmap that promises everything this quarter is a credibility liability.

## OKRs vs KPIs
- **KPIs** = ongoing health metrics you always watch (retention, uptime, CAC). **OKRs** = time-boxed change goals (Objective = qualitative aim; Key Results = 3-5 measurable outcomes).
- KRs measure outcomes (activation +15%), not output (ship 5 features). Grade 0.0-1.0; 0.7 is "good" for stretch OKRs.
- North-star metric: one leading measure of delivered customer value (e.g. weekly active teams, nights booked); decompose into an input tree the team can move.
- Avoid vanity metrics (raw signups, pageviews); prefer ratio/cohort metrics that survive scaling.

## PRD essentials
- Problem + who has it + evidence; goals and explicit **non-goals**; success metrics with targets; user stories + acceptance criteria; scope/MVP vs later; dependencies, risks, open questions; rollout + guardrails.
- One-pager beats a novel; link to research, not paste it. A PRD nobody reads is a symptom of writing for archive not alignment.

## MVP scoping
- MVP = smallest thing that tests the core hypothesis with real users, not "v1 minus polish." Thin vertical slice over broad shallow one.
- Cut scope, not quality; a broken MVP teaches nothing. Concierge/Wizard-of-Oz MVPs validate demand before you build the backend.

## Metrics
- **AARRR** (acquisition, activation, retention, referral, revenue); fix activation + retention before pouring in acquisition.
- Activation = the "aha" moment; define it as a measurable event and time-box it (e.g. value within first session).
- Retention via cohort curves; a flattening curve = product-market fit signal. Retention type: N-day (consumer/daily use) vs unbounded/rolling (B2B/infrequent). NPS/CSAT for sentiment (lagging, not a north-star).
- Funnels: instrument each step, find the biggest drop-off, fix that conversion first. North-star metric decomposes into 3-5 movable input metrics teams own; pair inputs with guardrail metrics so an input isn't gamed at the system's expense.
- Leading vs lagging: instrument leading indicators you can act on this sprint.

## Product operating model
- Empowered product teams (Cagan): teams are given problems/outcomes and discover solutions — not a feature list to build. Needs a product/design/eng trio, direct customer access, and execs who set outcomes not features.
- Feature team / "mercenaries" = delivery of a prioritized backlog; empowered team = accountable for a metric. Output orgs ship a lot and move nothing.

## Org topology: platform vs feature teams
- Feature/experience teams own customer-facing outcomes; platform teams provide leveraged internal capabilities (APIs, infra, shared services) as products with internal customers + SLAs.
- Team Topologies types: stream-aligned, platform, enabling, complicated-subsystem; design team boundaries to minimize cognitive load + handoffs. Beware a platform built with no internal-customer demand.

## Pricing & packaging (basics)
- Value-based pricing > cost-plus or competitor-match; price to a value metric that scales with customer value (seats, usage, transactions).
- Packaging: good/better/best tiers; fence features by segment; anchor + decoy options. PLG: free/freemium/trial for self-serve adoption, monetize expansion (land-and-expand, watch NRR). Van Westendorp / conjoint to gauge willingness-to-pay; grandfather existing customers on price changes.

## Portfolio prioritization
- Allocate investment across horizons (Three Horizons: core / adjacent / transformational), e.g. a 70/20/10 split; don't let KTLO/run-the-business consume all capacity.
- Fund outcomes/bets, not just projects; kill losing bets fast (venture mindset). Balance run vs grow vs transform explicitly at the portfolio level.

## Sunsetting / end-of-life
- Deprecate features/products with low usage + high maintenance; a feature nobody uses still costs (maintenance, cognitive load, support surface).
- EOL process: measure usage -> announce + timeline -> provide a migration path -> comms to affected users -> sunset -> remove code/flags. Frees capacity and shrinks surface area.

## Experiment design
- Hypothesis -> metric -> minimum detectable effect -> sample size/power BEFORE launch; pick one primary metric + guardrails.
- Run to significance and full business cycles; don't peek-and-stop (inflates false positives — use sequential testing if you must peek).
- Beware Simpson's paradox, novelty effect, and network interference in marketplaces.

## Build vs buy
- Buy/commodity for non-differentiating capability; build only your core differentiation. Weigh TCO: integration, maintenance, lock-in, opportunity cost — not just license price.
- Buy-then-build: unblock now with a vendor, replace if it becomes core.

## Technical debt tradeoffs
- Debt is a loan: fine for speed if you service the interest. Track it explicitly; allocate a standing % of capacity (e.g. 20%) to KTLO/paydown.
- Prioritize debt that slows delivery or raises incident risk; not all debt is worth paying. Make the cost visible to stakeholders in delivery terms.

## Stakeholder alignment
- Map stakeholders by influence x interest; RACI for decision rights. Pre-align 1:1 before the big meeting ("no surprises").
- Decision memo/one-way vs two-way door framing; write the recommendation + options + tradeoffs, drive to a dated decision.
- Manage up with outcomes and tradeoffs, not status theater; escalate blockers early with a proposed path.

## Failure modes -> Fix
- **Feature factory**: shipping output, no outcome. Fix: tie roadmap items to metrics; kill features that don't move them.
- **HiPPO-driven roadmap**: highest-paid-person's opinion wins. Fix: RICE/WSJF + evidence; make the tradeoff explicit.
- **Roadmap as dated promises**: every slip burns trust. Fix: now/next/later by confidence; commit near-term, direction long-term.
- **Building for the loudest customer**: one enterprise logo distorts the product. Fix: weight by segment/market size, not volume of asks.
- **No discovery**: build then learn nobody wanted it. Fix: dual-track; RAT before build.
- **Vanity metrics**: signups up, retention flat. Fix: cohort retention + activation as the real gauge.
- **Gold-plated MVP**: 6 months to "minimum." Fix: thin vertical slice; concierge/Wizard-of-Oz to test demand.
- **OKRs = task list**: KRs are outputs. Fix: rewrite KRs as measurable outcomes; separate from the delivery backlog.
- **Ignored tech debt**: velocity quietly craters. Fix: standing paydown budget; surface debt cost in delivery terms.
- **Peeking at A/B tests**: false wins. Fix: pre-set sample size + significance; sequential testing if peeking is required.
- **Analysis paralysis**: research forever, ship never. Fix: time-box discovery; reversible (two-way door) decisions move fast.
- **Vision/strategy vacuum**: roadmap is a request queue, teams optimize locally. Fix: explicit vision + where-to-play/how-to-win choices; say no on purpose.
- **Everything is priority-one**: no focus, constant thrash. Fix: force-rank; portfolio % allocation across horizons; cap WIP.
- **Feature teams told what to build**: outcomes never move despite shipping. Fix: give empowered teams problems + a metric, not a spec.
- **Platform built with no internal customers**: unused framework, sunk cost. Fix: treat platform as a product; validate internal demand; set SLAs.
- **Cost-plus pricing, never revisited**: leaves money on the table + mis-signals value. Fix: value-based pricing to a scaling metric; test WTP; iterate packaging.
- **Never sunsetting**: bloated surface, maintenance + cognitive drag. Fix: measure usage; deprecate low-value features with a migration path.
