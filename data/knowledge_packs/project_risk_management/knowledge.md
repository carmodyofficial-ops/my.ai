# Project Risk Management
## Risk vs issue
- Risk = uncertain future event with a probability and an impact (may not happen). Issue = a risk that has materialized (now, certain) — manage via issue log / corrective action.
- Risks can be threats (negative) or opportunities (positive). Assumptions and constraints are risk sources.
## Risk register (the core artifact)
- Columns: id, description, category, probability (1-5), impact (1-5), score (P×I), response, owner, trigger, residual risk, status.
- Write descriptions as cause -> risk event -> effect: "Because [cause], [event] may occur, leading to [impact]."
- Example row: `R-07 | Because a key vendor is single-source, delivery may slip, delaying UAT | Schedule | P4 | I5 | 20 | Mitigate: dual-source | Ops Lead | vendor misses milestone-2 | High | Open`.
## Qualitative analysis (P×I matrix)
- Score = Probability × Impact on a 5×5 grid; rank/prioritize by score. Green/Yellow/Red zones set attention.
- Fast, subjective, first-pass triage. Set a threshold above which a response plan is mandatory.
## Quantitative analysis
- EMV (Expected Monetary Value) = Probability × Impact($). Threats negative, opportunities positive. Sum for contingency sizing.
- Example: 30% × -$50k = -$15k EMV; a $5k mitigation that removes it is worth it.
- Decision tree: EMV across branches to choose the option with best expected value (fold back from leaves).
- Monte Carlo: simulate schedule/cost thousands of times over input distributions -> probability of hitting a date/budget (e.g. P80 completion); reveals path convergence risk.
- Sensitivity analysis (tornado diagram): which variables drive the most outcome variance.
## Response strategies
- Threats: Avoid (eliminate cause / change plan), Mitigate (reduce P or I), Transfer (insurance, warranty, fixed-price contract — cost stays), Accept (active = contingency reserve, passive = do nothing), Escalate.
- Opportunities: Exploit (make it happen), Enhance (raise P/I), Share (partner/JV), Accept, Escalate.
## RAID log
- Risks, Assumptions, Issues, Dependencies — one consolidated tracking log. Sometimes A = Actions.
- Assumptions that fail become risks/issues; dependencies are external commitments that can block you.
## Reserves
- Contingency reserve: for identified risks (known-unknowns); sized from EMV/quantitative analysis; part of the cost baseline; PM controls.
- Management reserve: for unidentified risks (unknown-unknowns); outside the baseline; sponsor/management controls; typically 5-15%.
## Triggers, owners, secondary & residual
- Trigger = the early-warning condition that a risk is about to occur; each risk needs one.
- Owner = one accountable person per risk (not "the team"); owns monitoring + executing the response.
- Residual risk = what remains after the response is applied. Secondary risk = a new risk introduced by the response itself (e.g. transferring to a vendor creates dependency risk).
## Process
- Plan -> Identify (brainstorm, checklists, interviews, SWOT, assumptions analysis) -> Qualitative -> Quantitative -> Plan responses -> Implement -> Monitor.
- Review the register every iteration; risk exposure should trend down as the project progresses.
## Agile / lean risk handling
- Iterations reduce risk structurally: short feedback loops surface problems early; highest-risk items pulled forward (risk-based backlog ordering).
- Spikes de-risk technical unknowns; a walking skeleton proves the risky architecture end-to-end first.
- RAID/risk board reviewed at retrospectives; impediment log doubles as an issue log.
## Reserve sizing example
- Three risks: R1 40%×$20k=$8k, R2 25%×$40k=$10k, R3 10%×$100k=$10k -> contingency ~$28k EMV.
- Add a separate management reserve (e.g. 10% of baseline) for the unknown-unknowns not in the register.
## Identification techniques
- Brainstorming, Delphi (anonymous expert consensus), interviews, checklists/prompt lists, assumptions & constraints analysis.
- SWOT (strengths/weaknesses/opportunities/threats), root-cause analysis, pre-mortem ("assume we failed — why?").
- Cause-and-effect (Ishikawa/fishbone), RBS (risk breakdown structure) to categorize by source (technical/external/org/PM).
## Risk categories
- Technical, external (vendor/market/regulatory), organizational (resources/funding/priorities), project management (planning/estimating/controls).
- Known-unknowns (identified, handled by contingency) vs unknown-unknowns (handled by management reserve).
## Risk attitude & appetite
- Risk appetite = amount of risk the org will pursue; tolerance = acceptable variation; threshold = the trigger to act.
- Utility theory: risk-averse, risk-neutral, risk-seeking stakeholders value the same EMV differently; align responses to appetite.
## Monitoring
- Track exposure trend over time; a risk burndown / exposure chart should decline as the project matures.
- Reassess at each phase gate + iteration; audit response effectiveness; watch for trigger conditions firing.
## Pitfalls -> Fix
- **Risk register written once, never reviewed**: goes stale, new risks unseen. Fix: review top risks every iteration; close resolved, add emerging, re-score.
- **Logging issues as risks (or vice versa)**: response is wrong. Fix: has it happened? Issue log + corrective action. Might it? Risk register + response plan.
- **Vague risk statements ("project might fail")**: not actionable. Fix: use cause -> event -> effect; make it specific and measurable.
- **No owner or "team owns it"**: nobody acts. Fix: assign one accountable owner per risk.
- **Response ends at "Mitigate" with no action**: strategy named, nothing done. Fix: define concrete mitigation actions with owner + due date; track like tasks.
- **Ignoring residual and secondary risk**: mitigation creates new exposure that's untracked. Fix: log residual + secondary risks after each response.
- **P×I scores treated as precise dollars**: false precision from subjective ordinals. Fix: use qualitative for triage; use EMV/Monte Carlo for numbers.
- **No contingency reserve, or padding hidden in estimates**: overruns look like failure; buffers vanish. Fix: size a visible contingency reserve from EMV; separate management reserve.
- **Only tracking threats, never opportunities**: leaves value on the table. Fix: capture opportunities with exploit/enhance/share responses.
- **No triggers defined**: risks noticed only after they hit. Fix: define an early-warning trigger and monitor it.
- **Risk management done once at kickoff**: exposure changes over time. Fix: make risk review a standing agenda item; watch the exposure trend.
- **Contingency and management reserve conflated**: PM spends the sponsor's buffer or vice versa. Fix: keep them separate with distinct control authority.
