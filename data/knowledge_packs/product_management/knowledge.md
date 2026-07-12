# Product Management: Request -> Buildable Spec

## 1. Start with the problem, not the solution
- Define the **job to be done**: *who* (specific user), *what pain/context*, *what outcome* they hire the product for. No solution yet.
> User: on-call eng. Pain: misses alerts at night. Outcome: never miss a SEV1.
- JTBD framing: "When <situation>, I want to <motivation>, so I can <expected outcome>." Solutions are hypotheses; the job is stable.

## 2. Discovery vs delivery
- **Discovery** (are we building the right thing?): talk to users, observe behavior, test riskiest assumptions with cheap experiments (prototype, fake-door, concierge) *before* committing eng. Continuous, not a phase.
- **Delivery** (are we building the thing right?): specs, build, ship, measure. Run both in parallel — discovery de-risks the next delivery.
- De-risk four dimensions: **value** (will they use it?), **usability** (can they?), **feasibility** (can we build it?), **viability** (does it work for the business?).

## 3. User stories + acceptance criteria
- `As a <role>, I want <goal> so that <benefit>.` Acceptance = **Given/When/Then**, testable, unambiguous.
> Given a SEV1 fires, When I'm on-call, Then I get a push within 30s.
- "Fast" / "easy" / "intuitive" aren't criteria — numbers and states are. Spec edge/error states (empty, offline, duplicate, denied, timeout), not just the happy path.

## 4. Prioritize
- **RICE** = Reach × Impact × Confidence / Effort — forces you to quantify and expose low-confidence bets.
- **MoSCoW**: Must / Should / Could / Won't (Won't = explicitly on record).
- **Impact×Effort 2×2** -> do high-impact/low-effort first; question high-effort/low-impact.
- **Kano** (basic/performance/delighter) to balance table-stakes vs differentiators. Weigh **cost of delay** for time-sensitive bets. Prioritize by evidence + strategy, not the loudest stakeholder.

## 5. Roadmap vs backlog
- **Roadmap**: outcome/theme-oriented, communicates direction + why (now/next/later or by problem), not a dated feature-commit list. Tie items to goals.
- **Backlog**: prioritized, groomed list of concrete work (stories/bugs/tasks) feeding delivery. Keep it small and current; a 300-item backlog is a graveyard, not a plan.

## 6. Write the spec / PRD
- Contents: problem + who + why now, goals & **non-goals** (explicit, so scope can't drift silently), user stories + acceptance criteria, success metrics + targets, key flows/edge cases, dependencies/risks/open questions, rollout plan.
- Capture the **why** (survives when details change). Specific, measurable, testable. Living doc — update as you learn; link designs/data, don't duplicate.

## 7. MVP scoping
- Smallest thing that delivers core value **and lets you learn** the riskiest assumption. Cut the rest to "later" — don't delete it.
- "Viable" = actually usable/valuable, not a broken slice; thin but complete over one polished corner. Prefer a narrow slice that proves the loop to a wide shallow one.

## 8. Metrics
- **North-star**: one metric capturing delivered user value (e.g. weekly active teams collaborating), leading revenue.
- Funnel: **activation** (first value / aha moment), **retention** (do they come back — the truest signal), engagement, referral, revenue. Pick leading (predictive) + lagging (confirming) pairs; set targets up front.
- Instrument before launch. **No metric = you can't tell ship from fail.** Avoid vanity metrics (raw signups/pageviews) with no decision attached; prefer rates/cohorts to totals.

## 9. Stakeholder alignment & saying no
- Align early: shared problem statement, goals, and success criteria; make tradeoffs (scope/time/quality/cost) explicit — give stakeholders options, not a flat yes/no.
- Say no by tying to strategy + opportunity cost ("yes, and it displaces X") and by asking for the underlying need. Trace the literal ask to the JTBD; offer the better thing.
> Ask: "add CSV export." Need: "see totals" -> a dashboard beats export.

## 10. Experiment mindset
- Frame features as hypotheses: "We believe <change> will cause <outcome>, measured by <metric>; we're wrong if <threshold> not hit." A/B test where traffic allows; otherwise pre/post with a guardrail metric.
- Ship to learn, define the kill/scale criterion before launch, and actually check the result — most ideas don't move the metric.

## 11. User research & evidence
- Talk to users about problems/behavior, not features ("tell me about the last time you…"); avoid leading questions and hypotheticals ("would you use…" over-predicts). Watch what they do > what they say.
- Mix qual (why — interviews, session replays, support tickets) with quant (what/how many — analytics, cohorts, funnels). Small-n qual finds the problem; quant sizes it.
- Continuous discovery: a steady cadence of user contact beats a big upfront research phase.

## 12. Working with engineering & design
- Bring the problem + constraints + success criteria; let eng/design own the solution — don't hand down implementation. Estimate together; treat estimates as ranges.
- Slice work so each increment ships value and is demoable; avoid month-long branches with no user feedback. Groom the backlog with the team, not in isolation.

## Pitfalls -> Fix
- Building without validation -> test the riskiest assumption cheaply (prototype/fake-door/interview) before committing eng.
- Feature factory (shipping output, not outcomes) -> tie every item to a problem + success metric; measure impact, kill what doesn't move it.
- Vanity metrics -> pick actionable rate/cohort metrics tied to a decision; track retention, not just signups.
- No success criteria -> define target metric + threshold *before* build; instrument first.
- Scope creep / gold-plating -> explicit non-goals, MVP cut, change-control on additions; polish what matters, not what's easy.
- Solutioning before the problem -> restate JTBD; separate problem from solution.
- Vague/untestable requirements -> Given/When/Then, numbers and states.
- Ignoring non-happy-path -> spec empty/error/denied/offline/timeout states.
- Roadmap as a dated feature promise -> outcome/theme roadmap with confidence bands.
- Building what's asked vs what's needed -> trace to the real need; present tradeoffs.
