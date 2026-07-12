# Think Clearly, Learn Fast

## First principles
- Derive from what's actually true *here*; don't paste a prior solution onto a new shape. Ask "what forces this? what's the irreducible constraint?"
- Strip to primitives: physics, cost, contracts, invariants. Rebuild up. e.g. "battery = $/kWh of raw materials," not "batteries cost $X because they always have."
- Separate the *law* (can't change: latency of light, API rate limit) from the *convention* (can change: chosen framework, current schema).

## Decomposition
- Split into sub-problems that don't depend on each other; solve/parallelize separately. Test the cut: if solving A changes B's answer, the seam is wrong.
- MECE the space (mutually exclusive, collectively exhaustive) so no case is double-counted or dropped.
- Issue tree / logic tree: branch the question until leaves are answerable by lookup or one measurement.

## Working backward
- State the goal concretely, ask "what must be true one step before?" Repeat back to now. Turns an open search into a short chain.
- Means-ends analysis: name the gap between current and goal state; pick the operator that shrinks it most.
- Solve a smaller/known instance first (n=1, 2), then generalize.

## Hypotheses + falsification
- Hold 2-3 rival hypotheses at once. For each, name the observation that would *kill* it, then go look for that. Confirming evidence is cheap and lies.
- Strong inference: design the one test whose outcome eliminates the most hypotheses. Diagnostic > confirmatory.
- Prefer the cheapest disconfirming test first (bisect, toggle one variable, check the log).
- An unfalsifiable claim ("it's flaky," "users won't like it") predicts nothing — force it to name an observable.

## Explicit assumptions (know / assume / check)
- Tag every claim: **know** (verified here), **assume** (plausible, untested), **must-check** (load-bearing + unverified). Bugs and bad bets hide in unmarked assumes.
- Rank must-checks by (impact if wrong × probability wrong); verify the top one before building on it.

## Problem framing
- The frame decides the answer. Restate the problem 2-3 ways before solving; "how do we reduce support tickets" vs "how do we make the product not need support" open different solution spaces.
- Ask "what problem is this actually solving, for whom?" before "how do I build it." Solving the stated problem perfectly is worthless if it's the wrong problem.
- Separate symptom from cause: five-whys drills from the visible failure to the root; fix the root, not the symptom.
- Widen then narrow: diverge (many options, no judgment) before you converge (pick). Mixing the two kills good options early.

## Analogical + Bayesian reasoning
- Analogy: map a solved problem onto the new one; check the mapping holds (which relations transfer, which break). Analogy generates hypotheses, it doesn't prove them.
- Bayesian update: start from the base rate (prior), move toward the evidence in proportion to how *diagnostic* it is. Weak evidence should barely move you; ignore neither prior nor data.
- Likelihood ratio: ask "how much more likely is this observation if H is true vs false?" Ratio near 1 = uninformative, don't update.
- Steelman before you reject: state the opposing view in its strongest form; if you can't, you don't understand it well enough to dismiss it.

## Estimation (Fermi)
- Estimate orders of magnitude before precise calc — catches 100x errors instantly. e.g. "10k rows × 1KB ≈ 10MB, fits memory"; "1M req/day ≈ 12/s avg, ~10x peak."
- Decompose into factors you can bound, multiply, round to 1 sig-fig. Sanity-check against a known anchor.
- Carry units; if they don't cancel, the model is wrong.

## Edge / extreme cases
- Enumerate: 0, 1, empty, huge, negative, null, duplicate, concurrent, unsorted, unicode, timezone/DST, off-by-one boundaries.
- Push each variable to its limit — behavior at extremes reveals the hidden assumption.

## Decisions under uncertainty
- List options; find the **one axis** that actually decides. Ignore the rest.
- Optimize **expected value** (Σ prob × payoff), not best case or worst case. Weight by calibrated probability, not vividness.
- **Base rates first**: anchor on the reference class ("how often does *this kind* of project ship on time?"), then adjust for specifics. The inside view alone is overconfident.
- **Reversible vs irreversible** (one-way vs two-way door): reversible → decide fast, try it, learn. Irreversible/costly → slow down, gather evidence, widen options.
- Value of information: only pay for data that would *change* the decision. Otherwise decide now.
- Expected value of options: keep cheap optionality when uncertainty is high; commit when it collapses.

## Explore vs exploit
- Early / cheap trials / long horizon → explore (sample widely, tolerate variance). Late / expensive / short horizon → exploit (bank the known-best).
- Heuristics: ε-greedy (mostly best, occasionally random), or optimism-under-uncertainty (try the option you know least about). Don't over-exploit a local optimum before mapping the space.

## Mental models (portable lenses)
- Inversion: "how would this fail?" — solve for avoiding the failure. Second-order effects: "and then what?"
- Bottleneck / theory of constraints: only the limiting step moves the outcome; optimizing elsewhere is waste.
- Marginal thinking: judge the next unit, not the average. Opportunity cost: every yes is a no to the best alternative.
- Pareto (80/20), leverage points, feedback loops, Occam (fewest entities), Hanlon (incompetence before malice).

## Debiasing
- **Confirmation** → actively seek disproof; assign someone red-team. **Anchoring** → re-estimate from scratch before seeing the number. **Sunk cost** → judge only on future value; ignore what's spent. **Availability/recency** → check base rates, not the vivid last example. **Overconfidence** → give 90% ranges, track calibration. **Framing** → restate the choice in gains *and* losses.
- Premortem: assume it already failed; list why. Consider-the-opposite: argue the other side before deciding.

## Metacognition
- Notice the *feeling* of confidence ≠ correctness; name your confidence as a number, then check calibration against outcomes over time.
- Rubber-ducking: explain the problem aloud/in writing step by step; the exact sentence you can't finish is the gap.
- Checklists for known-failure-prone steps; postmortems to update the checklist.
- Watch for the two failure modes of thinking: too fast (System-1 pattern-match on a hard, novel problem) and too slow (deliberating a trivial reversible call). Match effort to stakes × novelty.
- Know when to stop: you've reasoned enough when the next hour of thinking is less valuable than an hour of testing the current best guess. Then act and let reality correct you.
- Track your predictions in writing; ungraded intuition never calibrates. A prediction log is the cheapest debiasing tool.

## Learn fast
- **Map then drill**: sketch the ~5 big pieces + how they connect before any detail. Model first, trivia last.
- **Trace one real example** end-to-end through the actual system before reading abstract docs.
- **Learn by doing**: smallest experiment that returns signal — run it, read the error.
- **Deliberate practice**: work just past current ability, on isolated sub-skills, with immediate feedback and correction. Not mere repetition.
- **Spaced retrieval**: recall from memory at expanding intervals (1d, 3d, 1w) — testing beats re-reading. Interleave related topics rather than blocking one.
- **Teach it back** (Feynman): explain in plain words to a novice; stumbling marks the gap; fill it and repeat.

## Pitfalls -> Fix
- Jumping to first plausible answer -> generate a 2nd and 3rd before committing.
- Confirmation bias -> name the observation that would kill your view; go look for it.
- Anchoring -> estimate independently before exposure to any number.
- Premature convergence -> keep 2+ hypotheses live until one is falsified.
- Analysis paralysis on reversible calls -> classify the door; if two-way, ship and learn.
- Unfalsifiable claim -> force it to predict an observable, or discard it.
- Sunk cost -> decide from here forward; past spend is gone either way.
- Ignoring base rates -> start from the reference class, then adjust.
- Memorizing trivia before the model -> build the map first.
- Optimizing a non-bottleneck -> find the constraint, work only there.
