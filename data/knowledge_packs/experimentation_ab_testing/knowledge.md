# Experimentation & A/B Testing

## Hypothesis + metrics
- State a directional hypothesis: *"Change X will increase metric M by ≥ MDE because <mechanism>."* Pre-register before launch.
- **Primary metric** (OEC): one decision metric, sensitive + aligned to long-term value (e.g. conversion, revenue/user, retention). Avoid vanity metrics.
- **Guardrail metrics**: must-not-harm counters — latency, crash rate, unsubscribe, revenue, error rate. Ship only if guardrails hold.
- **Secondary/diagnostic**: explain *why* the primary moved (funnel steps, engagement).
- Prefer metrics that are sensitive (move with real effects), robust (low noise), and hard to game.

## Randomization + units
- **Randomization unit** = level of assignment (user, session, cookie, device, cluster). Analyze at the SAME unit you randomized on (else variance is wrong).
- User-level (persistent) avoids inconsistent experience + contamination; session-level gives more units but leaks across a user's sessions.
- Randomize via a hash of `unit_id + experiment_salt` → stable, independent buckets. Check assignment is 50/50 as intended.
- **A/A test** to validate the pipeline: no true effect → false-positive rate ≈ α, balanced buckets, no SRM.
- **SRM (Sample Ratio Mismatch)**: observed split ≠ designed (chi-square p<0.001) → broken assignment/logging; results invalid, do NOT trust. Investigate first.

## Sample size, power, MDE
- Determine `n` BEFORE launch from: significance `α` (0.05), **power** `1−β` (0.80), **MDE** (smallest effect worth detecting), baseline rate + variance.
- Proportion (per arm): `n ≈ 16·p(1−p)/δ²` for α=0.05, power=0.80 (δ = absolute MDE). Smaller MDE → quadratically more traffic.
- Continuous (per arm): `n ≈ 16·σ²/δ²`. Higher variance → more `n`.
- Runtime = `n / daily_eligible_traffic`, but run **≥1–2 full weeks** to cover weekly seasonality regardless.
- **Underpowered** test → can't detect real effects; a null result is inconclusive, not "no effect."

## Significance, CIs, decisions
- Compute effect (treatment − control), **CI**, and p-value. Report the CI + effect size, not just "significant."
- Two-proportion z-test / Welch t-test / bootstrap. Use **delta method** or cluster-robust SE when analysis unit ≠ randomization unit (ratio metrics like clicks/session).
- Significant ≠ meaningful: check the effect clears MDE and is worth the cost. A tight CI around ~0 = real evidence of no meaningful effect.

## Sequential testing + peeking
- **Peeking problem**: repeatedly checking a fixed-horizon test and stopping at first p<0.05 inflates Type I far above α (can exceed 30%).
- Fixes: (a) fix `n`/duration upfront and check once; (b) **sequential methods** that permit continuous monitoring — always-valid p-values, **mSPRT**, group sequential (O'Brien-Fleming / Pocock alpha-spending), Bayesian with decision rules.
- Never eyeball results and stop early on a fixed-horizon design.

## Novelty, primacy, seasonality
- **Novelty effect**: users react to change itself; early lift decays. **Primacy effect**: users need time to adapt; early results understate. → run long enough; inspect the effect's time trend; segment new vs returning users.
- Cover full weekly cycles; watch for holidays/promos confounding the window.

## Segmentation + Simpson's paradox
- Pre-specify a few segments (platform, new/returning, geo) to avoid fishing; correct for multiple segment tests.
- **Simpson's paradox**: aggregate effect reverses within subgroups when segment mix differs between arms (often from SRM or triggering differences). → check for SRM, analyze on comparable populations, use the correct randomization-unit analysis.

## Network effects + interference
- SUTVA violated when a user's treatment affects control users (social, marketplace, communication, two-sided platforms) → standard A/B under/over-estimates.
- Mitigations: **cluster randomization** (randomize communities/regions/graph clusters), **switchback** tests (toggle whole system by time slice — marketplaces), ego-network/graph-cluster designs, geo experiments.

## CUPED variance reduction
- **CUPED**: use a pre-experiment covariate `X` (usually the same metric before the test) to remove predictable variance.
- `Y_adj = Y − θ(X − E[X])`, `θ = Cov(Y,X)/Var(X)`. Unbiased; reduces variance by `ρ²` → often 20–50% less needed traffic / faster tests. Covariate must be pre-treatment (no leakage). Regression adjustment / stratification are alternatives.

## Multiple metrics + comparisons
- Many metrics/variants/segments inflate false positives. Correct: **Bonferroni** (`α/m`, conservative FWER) or **Benjamini-Hochberg** (FDR) for many exploratory metrics.
- Keep ONE primary metric to avoid cherry-picking; treat the rest as diagnostic. Multi-arm tests: correct across arms.

## Ship / no-ship decision
- Ship if: primary metric significantly clears MDE, guardrails not harmed (or acceptable tradeoff), effect stable over time + across key segments, cost/complexity justified, SRM/A-A clean.
- No-ship / iterate: flat or negative primary, guardrail regression, underpowered/inconclusive, novelty-driven, or SRM detected.
- Document decision + expected impact; consider a holdback/holdout to measure long-term + cumulative effects post-launch.

## Staged rollout + ramp
- Ramp exposure gradually: 1% → 5% → 20% → 50% to catch catastrophic regressions early with limited blast radius (guardrails watched at each step).
- Ramping changes traffic mix over time — don't pool pre/post-ramp data naively; analyze the stable full-allocation window.
- Use a **holdback/holdout** (small % kept on control after launch) to measure long-term + cumulative treatment effects that short tests miss.

## Triggering + dilution
- **Trigger analysis**: include only users who reached the code path that could be affected (triggered), not all traffic → higher sensitivity, avoids dilution by unaffected users.
- Triggering must be logged identically in both arms (a control user "would have triggered") or you introduce bias/SRM. Analyze from the trigger point forward.
- **Dilution**: mixing unaffected users shrinks the measured effect toward 0; correct scope tightens the estimate.

## Quasi-experiments (when RCT impossible)
- **Difference-in-differences**: compare treated vs control group change over time; assumes parallel trends pre-treatment.
- **Regression discontinuity**: exploit a cutoff threshold; compares just above vs below.
- **Instrumental variables / synthetic control / interrupted time series** for observational causal estimates. Weaker than RCT — state assumptions.

## Bucketing + consistency
- Deterministic hashing keeps a user in the same bucket across sessions + across the experiment's life; changing salt or ID reshuffles and invalidates.
- Avoid **carryover**: prior experiments' effects lingering; re-randomize + wash-out between tests sharing units.
- Mutually exclusive layers / overlapping experiment framework (each experiment on an orthogonal hash) so concurrent tests don't confound.

## Bayesian A/B testing
- Model each arm's rate/mean with a posterior (e.g. Beta-Binomial for conversion); report **P(treatment > control)** and **expected loss** if you pick wrong.
- Decision rule: ship when `P(B>A)` exceeds a threshold (e.g. 95%) AND expected loss < a tolerance. Naturally supports continuous monitoring (no fixed-horizon peeking penalty) if the decision rule is pre-set.
- Priors let you incorporate history; weak/uninformative priors ≈ frequentist for large `n`. Reports the intuitive "probability B wins" that frequentist p-values do not.

## Common metric definitions
- **Conversion rate** (binary), **ratio metrics** (clicks/session, revenue/user — need delta-method SE), **count** (events), **continuous** (time-on-page, revenue — often skewed → cap/winsorize or log, or use ratio-of-means).
- Winsorize/cap heavy-tailed revenue to reduce variance + outlier dominance; document the cap. Report both capped + raw as a sanity check.

## Pitfalls -> Fix
- **Peeking / optional stopping** (stop at first significant) -> fix horizon + check once, or use sequential/always-valid methods.
- **Underpowered test → null called "no effect"** -> size for MDE/power upfront; report CI; "inconclusive" ≠ "no difference."
- **p-hacking** (many metrics/segments/variants, report the winner) -> one primary metric; pre-register; BH/Bonferroni correction.
- **Ignoring guardrails** (ship on primary lift while latency/revenue regress) -> gate ship on guardrails; monitor them every test.
- **SRM ignored** (imbalanced split trusted) -> chi-square SRM check; invalidate + debug before interpreting.
- **Wrong analysis unit** (randomize by user, test by session) -> analyze at randomization unit; cluster/delta-method SE for ratio metrics.
- **Novelty/primacy read as steady state** -> run ≥1–2 weeks; plot effect over time; segment new vs returning.
- **Simpson's paradox from segment mix** -> check SRM/triggering; compare comparable populations.
- **Interference/network spillover** (social/marketplace) -> cluster or switchback randomization; geo tests.
- **Too-short runtime** (day-of-week bias) -> full weekly cycles; avoid holiday windows.
- **Stopping the instant it's significant even if below MDE** -> require effect ≥ MDE + practical value, not just p<0.05.
- **No pre-registration** (HARKing) -> lock hypothesis, metrics, `n`, and analysis plan before launch.
- **Twyman's law ignored** (a too-good result) -> a surprising huge effect is usually a bug/logging error; verify instrumentation.
