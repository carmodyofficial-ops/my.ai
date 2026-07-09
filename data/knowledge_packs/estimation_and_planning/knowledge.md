# Estimation and Planning
## Relative vs absolute estimation
- Absolute: estimate in hours/days directly — precise-looking, anchors badly, poor at scale.
- Relative: size items against each other (this is ~2x that) — faster, more consistent, humans compare better than they measure.
- Story points = relative size blending effort + complexity + uncertainty/risk. Unitless; team-calibrated to a reference story.
## Story points + planning poker
- Modified Fibonacci: 1, 2, 3, 5, 8, 13, 20, 40, 100 (gaps force a decision, reflect growing uncertainty).
- Planning poker: everyone reveals simultaneously (blind) to avoid anchoring; discuss outliers (highest + lowest justify), re-vote to converge.
- Anchor to a reference/baseline story (e.g. "a login form = 3"). Split anything > 13; it's too big/uncertain for a sprint.
- T-shirt sizing (XS/S/M/L/XL): coarse relative sizing for roadmap/epic-level items before decomposition.
## Three-point / PERT
- Gather Optimistic (O), Most Likely (M), Pessimistic (P).
- Triangular mean = (O + M + P) / 3. PERT (beta) mean = (O + 4M + P) / 6 — weights most likely.
- Std dev = (P - O) / 6; variance = SD^2. Sum activity means for path estimate; sum variances (not SDs) then sqrt for path SD.
- Example: O=4, M=6, P=14 -> PERT = (4+24+14)/6 = 7; SD = (14-4)/6 = 1.67.
- ~68% within ±1 SD, ~95% within ±2 SD -> quote a range, not a point.
## Velocity forecasting
- Forecast = remaining backlog points / rolling-average velocity. Bound with min/max velocity for a date range.
- Reference-class forecasting: base the estimate on the actual distribution of similar past projects, not a bottom-up plan — counters optimism bias (Kahneman/Flyvbjerg outside view).
## #NoEstimates
- Concept: slice work into small, similar-sized items; forecast by counting throughput (items/sprint) instead of estimating points.
- Works when items are consistently small; forecasting via Monte Carlo on historical throughput.
- Trades estimation effort for slicing discipline; strong when requirements churn makes point estimates worthless.
## Estimation units & conversion
- Story points -> time only via velocity (points/sprint × sprint length); never a fixed hours-per-point ratio.
- Ideal days vs elapsed days: ideal = uninterrupted work; multiply by a load factor for calendar time.
- Function points / COCOMO: parametric models for large predictive estimates from size + cost drivers (legacy, heavy).
## Buffers vs padding (recap)
- Padding = hidden per-task safety (wasted). Buffer = aggregated, visible, managed reserve (useful).
- Contingency buffer for known risks; management/project buffer for aggregate variability (CCPM ~50% of stripped safety).
- Monitor buffer consumption (fever chart): green/yellow/red vs % complete signals whether to act.
## Capacity planning
- Capacity = team members × available days × focus factor (typical 0.6-0.8), minus PTO/holidays/meetings/support.
- Don't plan to 100% utilization — reserve slack for interrupts, spikes, and variability.
- Sprint commitment <= capacity; account for individual availability, not just team average.
## Padding vs buffers (Critical Chain)
- Hidden per-task padding is wasted: Parkinson's Law (work expands to fill time), student syndrome (start late), no early finishes reported.
- Critical Chain (CCPM): cut per-task safety, aggregate it into a shared project buffer (~50% of removed safety) at the chain's end; feeding buffers protect the critical chain where non-critical paths merge.
- Buffer is visible, managed, and shared — contingency for known-unknowns; management reserve for unknown-unknowns.
## Cone of uncertainty
- Estimate variability is widest at project start (~0.25x-4x) and narrows as work proceeds and unknowns resolve.
- Implication: don't commit firm dates from early estimates; re-forecast at each milestone with actuals.
## Wideband Delphi
- Anonymous iterative estimation: experts estimate independently, a moderator aggregates + shares (anonymized), re-estimate until convergence — reduces anchoring and dominance.
## Decomposition & rolling wave
- Decompose big work into smaller items; sum of small estimates beats one big-item guess (law of large numbers reduces error).
- Rolling wave planning: detailed near-term, coarse far-term; elaborate later work as it approaches.
- Spikes: timeboxed research to reduce uncertainty before estimating a risky item.
## Estimation biases -> Fix
- **Optimism bias / planning fallacy**: estimate the best case, ignore history. Fix: use the outside view (reference-class); ask "how long did similar work actually take?"
- **Anchoring**: first number spoken drags all estimates. Fix: blind reveal (planning poker); estimate independently before discussing.
- **Precision theater**: quoting "37.5 hours" implies false confidence. Fix: quote ranges/confidence; use point buckets, not decimals.
- **Padding every task secretly**: safety evaporates (Parkinson + student syndrome). Fix: aggregate into a visible project buffer (CCPM); manage the buffer, not each task.
- **Estimating in hours at scale**: brittle, false precision, slow. Fix: relative sizing (points/t-shirt); convert to time only via velocity.
- **Points converted to a fixed hours ratio**: recreates absolute estimating and enables cross-team comparison. Fix: keep points unitless; forecast with the team's own velocity.
- **Committing to the mean of a wide O–P spread**: 50% chance of overrun. Fix: commit to a percentile (P80) using PERT SD; widen the range with uncertainty.
- **Estimates become deadlines/commitments**: pressure inflates or corrupts them. Fix: separate estimate (probabilistic) from commitment (business decision with buffer).
- **One person estimates for the team**: misses complexity others see. Fix: whole-team estimation; the doers estimate.
- **No re-estimation as you learn**: cone of uncertainty ignored (±4x at start, narrows over time). Fix: re-forecast each iteration with actuals.
- **Summing task SDs instead of variances for a path**: overstates risk. Fix: sum variances, then take the square root.
- **Estimating large, vague items**: uncertainty dominates. Fix: split to <=13 points; spike unknowns before sizing.
