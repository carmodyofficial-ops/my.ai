# Roadmapping
## Roadmap types
- **Now/Next/Later** — horizon buckets, no dates. Best under uncertainty; "Now" = in-build/committed, "Next" = next 1-2 cycles, "Later" = directional bets. Confidence decreases left→right.
- **Timeline/Gantt** — calendar swimlanes with dates/milestones. Use ONLY for committed delivery with hard external dependencies (contracts, regulatory, hardware). High false-precision risk.
- **Theme/outcome-based** — organized by goals ("reduce churn 15%") not features. Ties to strategy; keeps solution space open.
- **Release plan** — version-scoped feature list (v2.1 contents + date). Downstream of roadmap, not the roadmap.
- **Kanban/portfolio** — for many parallel initiatives across teams.
## Strategy alignment
- Chain: `Vision → Strategy → OKRs → Roadmap items → Backlog`. Every roadmap item traces to an Objective/Key Result. If it doesn't ladder to a goal, cut it.
- Roadmap answers *why now* and *what outcome*, not *how* or *exact when*. Use opportunity-solution tree (Teresa Torres): Outcome → Opportunities → Solutions → Experiments.
- Confidence-tag items: committed / probable / exploratory. Communicate the tag, not just the item.
## Prioritization inputs
- **RICE** = (Reach × Impact × Confidence) / Effort. Reach in users/period; Impact scored 0.25–3; Confidence % ; Effort in person-months.
- **WSJF** = Cost of Delay / Job Size (SAFe). Cost of Delay = user/business value + time criticality + risk-reduction/opportunity.
- **MoSCoW** = Must / Should / Could / Won't (scope-cut tool, not ranking).
- **Opportunity scoring** (Kano-ish) = importance × (1 − satisfaction) → find underserved needs.
- **Kano** = basic / performance / delight classification.
- **Value vs effort 2×2** for quick triage; beware effort estimates dominating.
## Roadmap vs backlog vs release plan
- **Roadmap** — strategic, outcome-oriented, quarters/horizons, small #items, exec/customer audience.
- **Backlog** — tactical, prioritized story list, sprint-granular, team audience, volatile.
- **Release plan** — which stories ship in which version + date. Roadmap ≠ backlog dump; roadmap ≠ dated feature list.
## Stakeholder communication
- Tailor the artifact: execs want outcomes+bets; sales/customers want directional "Later" (never dates); eng wants sequenced dependencies.
- Present as hypotheses. State assumptions and what would change the plan.
- Run a regular roadmap review (monthly/quarterly) — roadmap is living, versioned, dated-last-updated.
## Managing change
- Re-prioritize on new evidence, not loudest voice (HiPPO). Log the *reason* a bet moved.
- Keep a "parking lot" for out-of-scope ideas so stakeholders feel heard without derailing.
- Version the roadmap; keep a changelog so no one is surprised.
## Discovery feeding the roadmap
- **Opportunity-solution tree**: single desired Outcome → mapped Opportunities (unmet needs from research) → candidate Solutions → Experiments. Prioritize opportunities, not features; keeps roadmap outcome-anchored.
- Dual-track: continuous discovery (interviews, prototypes) de-risks items before they enter "Now". Only well-validated bets get committed.
- **Story mapping** (Jeff Patton): user activities across the top, tasks down; slice horizontally to define release increments and walking-skeleton MVP.

## Prioritization, applied
- Score consistently across a batch; RICE/WSJF ranks *relative*, not absolute — recompute per planning cycle.
- Beware garbage-in: Reach/Impact are estimates; pair the number with a written rationale and a confidence %.
- **Cost of Delay** thinking: what does a week's delay cost? Often reorders "obvious" priorities; underpins WSJF and shortest-weighted-job-first sequencing.
- Reserve explicit capacity for tech-health/KTLO (keep-the-lights-on) so it competes fairly rather than starving.

## Formats & tools
- Tools: ProductPlan, Aha!, Productboard, Jira Product Discovery, Roadmunk; or a simple Now/Next/Later board (Trello/Notion). Tool ≠ strategy.
- Keep a single source of truth; generate audience views (exec, customer-facing, engineering-sequencing) from it.
- Label with "last updated" + version; treat the roadmap as a communication artifact, not a contract.

## Metrics
- Track outcome KRs, not feature ship-count. "Did shipping X move the metric?" — feed learnings back into next horizon.
- Leading vs lagging: pair a lagging goal (retention) with leading indicators (activation, week-1 usage) you can steer within a cycle.
- Roadmap health signals: % items tied to OKRs, forecast-vs-actual on committed items, discovery→delivery cycle time.

## Pitfalls -> Fix
- **Roadmap = dated feature list**: becomes a broken promise; teams optimize for shipping-on-date over outcome. Fix: outcome-based Now/Next/Later; commit to problems, not dated features.
- **False precision on far items**: "Q3 2027" for exploratory work implies certainty you lack. Fix: horizon buckets + confidence tags; dates only for committed near-term.
- **Feature factory**: roadmap is a wishlist with no goal linkage. Fix: require each item to trace to an OKR; kill orphans.
- **Output over outcome**: measuring velocity/#features shipped. Fix: define success metric per item before building; review whether the metric moved.
- **Sales-driven roadmap**: every big deal reshuffles priorities. Fix: reserve capacity buffer; route requests through prioritization framework, not directly onto the roadmap.
- **Set-and-forget**: annual roadmap never revisited, drifts from reality. Fix: cadence review, versioning, changelog.
- **Solution-first**: roadmap prescribes exact features, closing better options. Fix: frame as opportunities/outcomes; let discovery pick the solution.
- **Effort estimates dominate RICE/WSJF**: everything low-effort wins, strategy ignored. Fix: sanity-check top items against strategic bets; don't let a formula overrule judgment.
- **Over-committing "Now"**: no slack for support/bugs/discovery. Fix: allocate capacity (e.g. 70% roadmap / 20% tech-health / 10% discovery).
- **One roadmap for all audiences**: exec deck shown to customers leaks dates. Fix: maintain audience-specific views from one source of truth.
- **Confusing roadmap with backlog**: roadmap becomes a 200-item Jira export. Fix: roadmap = few strategic themes; backlog stays in the tracker.
- **Ignoring dependencies**: parallel items collide on shared platform work. Fix: sequence enabler/platform work explicitly; map cross-team dependencies before committing dates.
