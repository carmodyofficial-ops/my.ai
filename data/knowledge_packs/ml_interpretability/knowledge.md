# ML Interpretability & Explainability

## Why it matters
- **Trust/adoption**: stakeholders accept models they can inspect.
- **Debugging**: catch leakage, spurious correlations, mislabeled data (e.g. model keys on a hospital ID token instead of pathology).
- **Fairness/bias**: surface disparate reliance on proxies for protected attributes.
- **Regulation**: GDPR "right to explanation", EU AI Act high-risk transparency, US ECOA/FCRA adverse-action reasons (credit denials need reason codes).
- **Safety/robustness**: understand failure modes before deployment.

## Taxonomy (pick the right axis)
- **Global** (whole-model behavior) vs **Local** (single prediction).
- **Intrinsic** (model is self-explanatory) vs **Post-hoc** (explain a trained black box).
- **Model-specific** (uses internals, e.g. TreeSHAP, gradients) vs **Model-agnostic** (only I/O, e.g. LIME, KernelSHAP, permutation).

## Intrinsic / glass-box models
- **Linear/logistic regression**: coefficients = effect per unit feature (standardize first; sign+magnitude interpretable only for uncorrelated, scaled features). Log-reg coefs → log-odds; `exp(coef)` = odds ratio.
- **Decision trees**: follow the path = the rule. Small depth only.
- **GAMs / EBM** (Explainable Boosting Machine): additive shape functions per feature, near-black-box accuracy, plottable.
- **Rule lists / RuleFit**, **decision sets**: human-readable rules.
- Prefer intrinsic when accuracy is competitive — cheaper and faithful by construction.

## Feature importance (global)
- **Permutation importance**: shuffle one feature, measure metric drop on held-out data. Model-agnostic, needs no refit. Inflated/misleading under correlated features (shuffling breaks joint distribution → unrealistic rows).
- **Impurity/gain (trees)**: fast but **biased toward high-cardinality / continuous** features; computed on train data. Prefer permutation on validation.
- **Drop-column importance**: refit without feature; most accurate, most expensive.
- Importance ≠ causation; it's about the model's reliance, not the world.

## SHAP (SHapley Additive exPlanations)
- Game-theoretic: attributes prediction to features via **Shapley values** (average marginal contribution over all feature orderings). Unique solution satisfying local accuracy, missingness, consistency.
- **Additive**: `f(x) = base_value + Σ shap_i`. Local explanation sums to the prediction.
- **TreeSHAP**: exact, fast, polynomial for tree ensembles (XGBoost/LightGBM/RF). Default for tabular trees.
- **KernelSHAP**: model-agnostic, weighted local linear regression on coalitions; slow, approximate, needs background dataset.
- **DeepSHAP/GradientSHAP**: for neural nets (DeepLIFT-based).
- **Plots**: `summary_plot` (beeswarm — global importance + direction), `bar` (mean |SHAP|), `waterfall`/`force` (single prediction), `dependence` (feature vs SHAP, shows interactions), `interaction values`.
- **Background/reference** choice matters: interventional (marginal) vs conditional (tree_path_dependent) perturbation changes attributions.

## LIME
- **Local surrogate**: perturb around instance, weight by proximity, fit sparse linear model locally. Model-agnostic, works for tabular/text/image (superpixels).
- Explains one prediction with a few weighted features.
- **Unstable**: results vary with kernel width, sampling seed, #samples. Less rigorous than SHAP; faster to grasp.

## PDP & ICE
- **Partial Dependence Plot**: average model output as one/two features vary (marginalizing others). Shows global average marginal effect. **Assumes feature independence** — misleading with correlation (extrapolates to impossible regions).
- **ICE (Individual Conditional Expectation)**: one line per instance; reveals heterogeneity/interactions that PDP averages away. Use **centered ICE (c-ICE)** to compare shapes.
- **ALE (Accumulated Local Effects)**: robust to correlated features (uses local differences in a conditional distribution) — prefer over PDP when features correlate.

## Counterfactual explanations
- "Smallest change to x that flips prediction to desired class" (actionable/recourse). Should be **valid, sparse, close, actionable, plausible** (on-manifold). Libraries: DiCE, Alibi.
- Good for recourse ("increase income by X to be approved"); doesn't explain global logic.

## Deep-model explanations
- **Saliency/gradients**: `∂output/∂input`. Vanilla saliency is noisy. **Integrated Gradients** (path from baseline, satisfies completeness/sensitivity), **SmoothGrad** (averages noisy copies), **Grad-CAM** (class-discriminative heatmaps from conv activations).
- **Attention is NOT explanation** (Jain & Wallace): attention weights don't reliably indicate feature importance; can be permuted with same output.
- **Concept-based**: **TCAV** (testing with concept activation vectors) — sensitivity to human concepts (e.g. "stripes") rather than pixels.
- **Mechanistic interpretability** (LLMs): circuits, probing, sparse autoencoders for features, activation patching.

## Evaluating explanations
- **Faithfulness**: does the explanation reflect the true model? Test via **deletion/insertion** (remove top-attributed features → output should drop), infidelity, sanity checks (**model-parameter randomization test** — explanation must change when weights randomized; many saliency maps fail).
- **Stability/robustness**: similar inputs → similar explanations.
- **Human-groundedness**: does it help a human predict/simulate the model.
- No single ground truth — use multiple methods; agreement raises confidence.

## Interpretability vs accuracy
- Not always a tradeoff: on structured/tabular data, EBM/GBM often match black boxes. Tradeoff is real for perception/NLP.
- Consider **model distillation** into a glass box for explanation (surrogate global model) — but surrogate fidelity must be checked (R² of surrogate).
- **Anchors** (Ribeiro): high-precision IF-THEN rules that "anchor" a prediction (holds with ≥X% precision regardless of other features) — more actionable than LIME weights.
- **Global surrogate**: fit an interpretable model to the black box's predictions; report fidelity (agreement), not just accuracy.

## Method selection (quick guide)
- Tabular + trees/GBM → **TreeSHAP** (fast, exact) for local+global; permutation importance for global.
- Tabular, model-agnostic / any model → KernelSHAP (slow) or LIME (fast, unstable); PDP/ALE for shape.
- Correlated features → **ALE** over PDP; grouped/clustered SHAP.
- Deep vision → **Grad-CAM** + **Integrated Gradients**; sanity-check.
- Deep NLP / LLM → IG on embeddings, attention rollout (with caveats), probing, SAEs for mechanistic work.
- Need actionable recourse → **counterfactuals / Anchors**.
- Regulatory reason codes → SHAP top contributors or reason-code mapping from a monotonic GBM.

## Tooling
- **`shap`** (Lundberg): all SHAP variants + plots. **`lime`**. **`InterpretML`** (EBM + glassbox + blackbox). **`Alibi`** (counterfactuals, anchors, ALE, TrustScore). **`Captum`** (PyTorch: IG, DeepLIFT, GradCAM, occlusion). **`ELI5`**, **`eli5`/sklearn** permutation importance. **`PDPbox`/sklearn** PDP/ICE. **`What-If Tool`**, **`AIX360`** (IBM), **`Fairlearn`** (fairness).
- Reproducibility: fix seeds, pin background dataset, version explanation configs alongside the model.

## Fairness intersection
- Group-wise SHAP / importance to detect reliance on proxies (zip code ~ race). Combine with fairness metrics (demographic parity, equalized odds).
- Interpretability finds *how* a model discriminates; fairness metrics quantify *that* it does — use both.
- Watch for **fairwashing**: a plausible explanation that hides discriminatory behavior; require faithfulness checks.

## Pitfalls -> Fix
- **SHAP/PDP on correlated features** → attributions split arbitrarily among correlated inputs; PDP extrapolates off-manifold. **Fix**: cluster/drop redundant features, use ALE, use conditional/grouped SHAP, report correlation.
- **Reading importance as causal** → "feature X drives outcome" claim. **Fix**: importance = model reliance only; use causal inference (DAGs, do-calculus, RCTs) for causal claims.
- **Impurity importance trusted** → biased to high-cardinality/continuous, computed on train. **Fix**: permutation importance on a held-out set; watch correlated-feature inflation.
- **Explanation instability** (LIME/saliency vary by seed) → cherry-picked story. **Fix**: fix seeds, average over runs, report variance, prefer SHAP/IG with completeness.
- **Overtrusting saliency maps** → pretty heatmaps that are input-structure edge detectors, not model logic. **Fix**: run sanity checks (parameter/label randomization); use Grad-CAM + IG together.
- **Attention treated as importance** → **Fix**: use gradient×input or ablation, not raw attention.
- **Global explanation from few local ones** → **Fix**: aggregate SHAP over the dataset; don't generalize a single waterfall.
- **Explaining on training data / with default background** → leakage into explanation, base-value confusion. **Fix**: use representative held-out background; document reference set.
- **Cherry-picking favorable examples** for stakeholders → **Fix**: sample randomly + show failure cases; report faithfulness metrics.
- **Permutation importance with leakage/duplicates** → underestimates importance (correlated copy compensates). **Fix**: dedupe features, use grouped permutation.
- **Explaining a bad model** → faithful explanation of garbage. **Fix**: validate model performance first; interpretability is not a substitute for accuracy/validation.
- **Confusing local accuracy with correctness** → SHAP always sums to prediction even if model is wrong. **Fix**: separate "why this prediction" from "is it right".
- **KernelSHAP too slow / background too large** → hours per batch. **Fix**: use TreeSHAP for trees; subsample background (k-means summarize); explain a representative sample not all rows.
- **PDP hides heterogeneity** (opposite effects average to flat) → **Fix**: always plot ICE alongside PDP.
- **Explanation used to justify a decision post-hoc** (fairwashing) → **Fix**: require faithfulness metrics + audit on failure/edge cases, not just cherry-picked wins.
- **Interpreting standardized-away units** → coefficient magnitudes incomparable across differently-scaled features. **Fix**: standardize before comparing, or report per-SD effects.
