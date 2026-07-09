# Data Science Workflow

## Lifecycle (CRISP-DM)
1. **Business understanding** — define the decision/action the model informs; success metric tied to $ or user outcome, not just accuracy.
2. **Data understanding** — inventory sources, schema, volume, freshness, quality; EDA.
3. **Data preparation** — clean, transform, feature-engineer (usually 60–80% of effort).
4. **Modeling** — baseline → candidates; train/tune.
5. **Evaluation** — offline metrics + business alignment; error analysis.
6. **Deployment** — pipeline, monitoring, retraining. Iterate; it is a loop, not a line.
- Alternatives: TDSP, OSEMN (Obtain-Scrub-Explore-Model-iNterpret), ML lifecycle.

## Problem framing (do first, cheaply)
- Write the question as: *predict / classify / rank / cluster / estimate* **what**, for **whom**, to enable **which decision**.
- Choose target + unit of analysis explicitly. Regression vs classification vs ranking changes everything downstream.
- Define the metric BEFORE modeling; map to a business KPI. Decide the baseline (current heuristic/rule) to beat.
- Confirm data actually exists at prediction time (no future/leaked features). Estimate label availability + latency.
- Cost of errors: is FP or FN worse? Sets threshold + metric (precision vs recall).

## Data collection + cleaning
- **Missing data** mechanisms: **MCAR** (random — drop safe), **MAR** (depends on observed — impute), **MNAR** (depends on unobserved — model the missingness, add indicator). Impute median/mode or model-based (KNN, MICE); add `is_missing` flag. Fit imputers on train only.
- **Outliers**: detect via IQR fence, z-score `|z|>3`, isolation forest. Investigate cause before acting; cap/winsorize or transform rather than delete silently; keep if genuine.
- **Dedup**: exact + fuzzy (record linkage on normalized keys). Grouped duplicates (same user) must not split across train/test.
- Fix types, units, encodings, timezones; validate ranges + referential integrity; document assumptions.

## EDA
- Univariate: distributions (histogram/KDE), skew, cardinality, missingness per column. Target balance.
- Bivariate: correlation matrix (Pearson linear, Spearman monotonic), scatter, boxplots by category, target vs feature.
- Multivariate: pairplots, dimensionality reduction (PCA/UMAP) for structure/clusters.
- Look for leakage signals (a feature "too predictive"), data drift over time, seasonality, class imbalance.
- Always plot before trusting summary stats (Anscombe's quartet / Datasaurus: same stats, different data).

## Feature engineering
- **Encoding**: one-hot (low cardinality), ordinal (ordered), target/mean encoding (high cardinality — compute inside CV folds to avoid leakage), embeddings, frequency/count encoding, hashing.
- **Scaling**: standardize `(x−μ)/σ` for distance/gradient models (SVM, kNN, k-means, linear+reg, NN); trees are scale-invariant. Fit scaler on train only.
- **Transforms**: log/Box-Cox for skew; binning; datetime parts (dow, hour, is_holiday); cyclical `sin/cos` for hour/month.
- **Interactions + ratios**: domain-driven products/ratios often beat raw features.
- **Leakage traps**: target-derived features, post-outcome data, global aggregates computed before split, time features from the future. Any transform learning from data must be fit on train only (use `sklearn.Pipeline`/`ColumnTransformer`).

## Modeling
- **Baseline first**: majority class / mean / simple rule / logistic/linear. Never report a complex model without beating it.
- **Splits**: train (fit) / validation (tune) / test (touch once). Time series → chronological split, never shuffle.
- **Cross-validation**: k-fold (5/10) for robust estimates; **stratified** (preserve class ratio); **GroupKFold** (correlated groups); **TimeSeriesSplit**/walk-forward (temporal). Do all preprocessing inside the CV loop.
- Progression: linear/logistic → tree → random forest → gradient boosting (XGBoost/LightGBM/CatBoost, strong on tabular) → NN if justified.
- Hyperparameter search: grid → random → Bayesian (Optuna). Tune on validation/CV only. Prefer fewer params + early stopping.
- Handle imbalance: `class_weight`, resampling (SMOTE on train only), threshold tuning via PR curve.

## Evaluation + interpretation
- Pick metric by task/cost: classification (precision/recall/F1, ROC-AUC ranking, PR-AUC for rare positives, log-loss/calibration); regression (RMSE, MAE robust, R²). Accuracy misleads under imbalance.
- **Error analysis** > single number: slice by segment, inspect worst errors, confusion matrix, residual plots. Find where the model fails.
- Compare to baseline + confidence intervals (bootstrap). Check **calibration** (reliability curve) if probabilities are used for decisions.
- **Interpretation**: coefficients (linear), feature importance (gain/permutation — permutation is model-agnostic + less biased), **SHAP** (per-prediction additive attributions, direction + magnitude, handles interactions), partial dependence / ICE plots. Explain to stakeholders in domain terms.

## Communicating results
- Lead with the decision + recommendation, then evidence. State assumptions, limitations, uncertainty, and what could break it.
- Tie metric deltas to business impact ($, conversion, risk). Show a few interpretable examples, not just aggregate numbers.
- Quantify uncertainty (CIs); avoid overclaiming causality from correlational models.

## Reproducibility (notebooks → pipelines)
- Version: code (git), data (DVC/hashes/snapshots), model + params (MLflow/experiment tracker), environment (lockfile/Docker), random seeds.
- Notebooks for exploration; **refactor to scripts/pipelines** for anything repeated or shipped (hidden state + out-of-order cells break repro).
- Deterministic seeds; log configs + metrics per run; separate config from code. One command should reproduce a result.
- Package preprocessing + model as a single artifact (Pipeline) so train and serve share transforms — prevents train/serve skew.

## Model selection tradeoffs
- Accuracy vs interpretability vs latency vs cost. Linear/logistic + trees are interpretable + cheap; gradient boosting wins tabular accuracy; deep nets for images/text/sequence with enough data.
- Prefer the simplest model meeting the metric bar (Occam); complexity must earn its keep vs baseline.
- Small data → high-bias simple models + regularization + CV; big data → flexible models. Sparse/wide → L1/lasso. Nonlinear + interactions → trees/boosting.
- Ensembles (bagging reduces variance, boosting reduces bias, stacking blends) trade interpretability for accuracy.

## Deployment + monitoring
- Serve as batch (scheduled scoring) or online (real-time API); match training/serving features exactly (feature store prevents skew).
- **Monitor**: prediction distribution, input **data drift** (PSI, KS test), **concept drift** (target relationship changes → metric decay), latency, null rates, business KPI.
- Retrain on schedule or drift trigger; keep a champion/challenger; roll out behind a flag; log predictions for audit + future labels.
- Shadow-deploy new models against production traffic before switching.

## Data types + representation
- Structured/tabular (rows×columns), time series (ordered, autocorrelated), text (tokens/embeddings), images (pixels/CNN features), graph (nodes/edges), geospatial.
- Numeric (continuous/discrete), categorical (nominal/ordinal), datetime, boolean, high-cardinality IDs. Each drives different encoding + model choices.

## Experiment tracking + iteration
- Log every run: dataset version/hash, feature set, hyperparameters, metrics, artifacts (MLflow/W&B/DVC). Never rely on memory or notebook cell state.
- Change one thing per iteration to attribute gains; keep a leaderboard vs baseline; record failed ideas + why.
- Time-box exploration; ship the best-validated model, then improve in production behind monitoring — perfect offline is rarely worth the delay.

## Stakeholder + ethics checks
- Confirm the model's decision is actionable + acceptable to the business; align on metric before building to avoid rework.
- Check fairness across protected segments (disparate error rates), privacy/PII handling, and whether proxies encode bias. Document limitations + intended use.

## Pitfalls -> Fix
- **Data leakage** (fitting scaler/encoder/imputer on full data before split; target-derived or future features) -> fit inside CV on train only; use Pipeline; audit each feature's availability at prediction time.
- **No baseline** -> always report a trivial/heuristic baseline; a fancy model that barely beats it is not worth it.
- **Overfitting to the validation set** (repeated tuning against val) -> hold out a final untouched test set; use nested CV; limit tuning iterations.
- **Optimizing the wrong metric** (accuracy on imbalanced data) -> choose metric by error cost; use PR-AUC/F1/recall as appropriate.
- **Train/serve skew** (different preprocessing offline vs prod) -> ship the exact fitted Pipeline; test on prod-shaped data.
- **Trusting summary stats without plotting** -> always visualize (Anscombe/Datasaurus).
- **Temporal leakage / shuffling time series** -> chronological split + walk-forward CV.
- **Ignoring class imbalance / base rates** -> resample train, adjust threshold, report base-rate-aware metrics.
- **Unvalidated assumptions about data meaning** -> confirm column semantics/units/collection process with source owners.
- **Non-reproducible notebooks** (out-of-order cells, no seed) -> restart-and-run-all; seed; refactor to scripts.
- **Deleting outliers silently** -> investigate cause; document; winsorize instead of drop.
- **Confusing correlation-model importance with causation** -> state models are associational; use causal methods for interventions.
- **Reporting one metric with no uncertainty** -> bootstrap CIs + error slices.
