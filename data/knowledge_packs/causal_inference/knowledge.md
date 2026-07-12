# Causal Inference

Estimate the effect of an **intervention** (`do(X)`), not mere association. "Would Y differ **had** we changed X?" Prediction models `P(Y|X)`; causal inference models `P(Y|do(X))`.

## Core framework — potential outcomes (Rubin)
- Each unit has **potential outcomes** `Y(1)` (if treated) and `Y(0)` (if not). Observe only one → **fundamental problem of causal inference** (the other is the **counterfactual**).
- **ATE** = `E[Y(1) − Y(0)]` (average over population). **ATT** = `E[Y(1)−Y(0) | T=1]` (effect on the treated). **CATE** = effect conditional on covariates `X` (heterogeneity).
- Naive `E[Y|T=1] − E[Y|T=0]` = ATE **only if** treatment is independent of potential outcomes (RCT). Otherwise = causal effect + **selection bias**.

## RCT — gold standard
- Randomization makes `T ⟂ {Y(0),Y(1)}` → treated/control exchangeable → difference in means is unbiased ATE. Balances measured **and unmeasured** confounders in expectation.
- Not always feasible (ethics, cost, can't randomize price/policy) → observational methods + assumptions.

## Confounding & bias
- **Confounder**: common cause of both T and Y (age → both treatment choice and outcome). Ignoring it → biased. Must **adjust** for it.
- **Selection bias**: sample/conditioning depends on outcome or a collider.
- **Colliders**: common *effect* of two vars (`A → C ← B`). Conditioning on a collider (or its descendant) **creates** spurious association between A and B → do **not** control for colliders.
- **Mediator**: on the causal path `T → M → Y`. Controlling for it removes part of the true effect (blocks the indirect path) → underestimates total effect. Don't adjust for mediators when you want total effect.

## Causal graphs (DAGs)
- Nodes = variables, directed edges = direct causes. Encode assumptions explicitly; read off what to adjust.
- **d-separation**: path is blocked if it contains a non-collider you condition on, or a collider you don't condition on (and no descendant conditioned). X ⟂ Y | Z if all paths blocked.
- **Backdoor criterion**: to identify `T→Y`, block all "backdoor" paths (arrows into T) by conditioning on a set **Z** that (a) blocks every backdoor path, (b) contains no descendant of T. Then adjust for Z → causal effect identified.
- **Frontdoor criterion**: identify effect via a fully-mediating M even with unmeasured T–Y confounding, if M is unconfounded with Y and T only affects Y through M.
- Adjust for confounders + (optionally) pure predictors of Y; **never** colliders or mediators.

## Estimators (given ignorability + measured confounders Z)
- **Regression adjustment / g-formula**: model `E[Y|T,Z]`, predict both `T=1` and `T=0` for all, average difference. Sensitive to model misspecification/extrapolation.
- **Propensity score** `e(Z)=P(T=1|Z)`: scalar summary of confounders.
  - **Matching** treated↔control on `e(Z)` (nearest-neighbor/caliper) → compare like-with-like → ATT.
  - **IPW** (inverse propensity weighting): weight by `1/e` (treated), `1/(1−e)` (control) → pseudo-population where T⟂Z. Watch extreme weights → trim/stabilize.
  - **Stratification** on propensity deciles.
- **Doubly robust** (AIPW, TMLE): combine outcome model + propensity model; consistent if **either** is correct. Use with ML nuisance models → **double/debiased ML** (cross-fitting to remove overfit bias). Estimate CATE with causal forests, meta-learners (S/T/X-learner).

## Quasi-experiments (natural experiments)
- **Difference-in-Differences (DiD)**: treated vs control, before vs after. `ATT = (Ȳ_treat,post − Ȳ_treat,pre) − (Ȳ_ctrl,post − Ȳ_ctrl,pre)`. Key assumption: **parallel trends** (absent treatment, both groups would move in parallel). Check pre-trends; beware staggered adoption (use modern estimators: Callaway-Sant'Anna, not naive two-way FE).
- **Regression Discontinuity (RDD)**: treatment assigned by a cutoff on a running variable (score ≥ c → treated). Compare units just above vs just below → local ATE at cutoff. Assumes no manipulation of the running variable (McCrary density test) + continuity of potential outcomes at c.
- **Instrumental Variables (IV)**: instrument Z affects T but affects Y **only through T** (exclusion) and is **as-good-as-random** (independent of confounders), and is **relevant** (`Cov(Z,T)≠0`). 2SLS: regress T on Z (predict T̂), regress Y on T̂ → estimates **LATE** (effect on compliers). 
- **Synthetic control**: build a weighted combination of control units matching the treated unit's pre-period → counterfactual for a single treated unit (policy/region studies).

## Identification assumptions
- **Ignorability / conditional exchangeability**: `{Y(0),Y(1)} ⟂ T | Z` — no **unmeasured confounding** given Z. Untestable; the crux.
- **Positivity / overlap**: `0 < P(T=1|Z) < 1` for all Z — every covariate profile could receive either treatment. Violated → extrapolation. Check propensity distribution overlap.
- **SUTVA**: no interference (one unit's treatment doesn't affect another's outcome — violated by spillovers/network effects) + single well-defined version of treatment (consistency).

## Sensitivity analysis
- Since no-unmeasured-confounding is untestable, quantify robustness: **E-value** (how strong an unmeasured confounder must be to explain away the effect), Rosenbaum bounds, Manski partial-identification bounds, negative-control outcomes/exposures.

## Prediction vs causation
- A great predictor of Y is **not** necessarily a lever. Coefficients from a predictive/associational regression are **not** causal (they mix confounding, colliders, mediators). Adding more controls improves prediction but can *worsen* causal estimates (collider/mediator/M-bias). Variable selection for causation is driven by the DAG, not by fit/AIC/regularization.

## Pitfalls -> Fix
- **Interpreting regression coefficients as causal** ("controlling for everything"). Fix: draw the DAG, choose adjustment set by backdoor criterion; report as associational otherwise.
- **Controlling for a collider** → induced spurious association (selection/collider bias, incl. Berkson, M-bias). Fix: don't condition on common effects or their descendants; use DAG.
- **Controlling for a mediator** when you want the total effect → blocks part of the effect. Fix: exclude mediators (or do explicit mediation analysis for direct/indirect).
- **"Throw all variables into the model"** → includes colliders/mediators/post-treatment vars. Fix: never adjust for post-treatment variables; select via DAG.
- **Unmeasured confounding** silently biases everything. Fix: sensitivity analysis (E-value), negative controls, find an instrument/quasi-experiment, or randomize.
- **Positivity violation / poor overlap** → weights explode, extrapolation. Fix: trim/truncate propensity, restrict to common support, stabilized weights.
- **Weak instrument** (`Cov(Z,T)≈0`) → huge variance, bias toward OLS (first-stage F<10). Fix: check first-stage F; find stronger instrument; don't use weak IV.
- **Invalid instrument** (violates exclusion — affects Y directly, or is confounded). Fix: argue exclusion substantively; over-ID tests can't prove validity.
- **Parallel-trends violation** in DiD (pre-trends diverge). Fix: plot/event-study pre-trends; matching + DiD; synthetic control; modern staggered estimators (naive two-way FE is biased with heterogeneous timing).
- **RDD running-variable manipulation** / wrong bandwidth. Fix: McCrary density test, local-linear with optimal bandwidth, no covariate jumps at cutoff.
- **Confusing ATE/ATT/LATE** — IV gives LATE (compliers), RDD gives local effect at cutoff; not the population ATE. Fix: state the estimand and population it applies to.
- **SUTVA violation** (spillovers, network, general equilibrium). Fix: cluster-level randomization/analysis, model interference explicitly.
- **Simpson's paradox** — aggregate reverses within subgroups. Fix: the DAG tells you whether to aggregate or stratify; not automatic.
- **p-hacking multiple subgroups** as "heterogeneous effects". Fix: pre-register, correct for multiplicity, use principled CATE estimators.
```
