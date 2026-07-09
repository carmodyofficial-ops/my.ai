# Machine Learning Fundamentals

## Learning paradigms
- **Supervised**: labeled `(X, y)`; learn `f: X→y`. Regression (continuous `y`) + classification (discrete `y`).
- **Unsupervised**: no labels; find structure. Clustering (k-means, DBSCAN, hierarchical), dimensionality reduction (PCA, t-SNE, UMAP), density estimation.
- **Reinforcement**: agent takes actions in environment, maximizes cumulative reward `Σ γ^t r_t`; policy `π(a|s)`; Q-learning, policy gradients.
- **Semi/self-supervised**: few labels + many unlabeled; pretext tasks generate pseudo-labels.

## Data splits + leakage
- Split **train / validation / test** (e.g. 70/15/15). Train fits params; val tunes hyperparams + early stopping; test = final unbiased estimate, touched once.
- **Leakage** = info from val/test (or future) contaminates training → optimistic scores that don't generalize. Causes: fitting scaler/imputer/encoder on full data before split; target-derived features; duplicate/grouped rows split across sets; time-series shuffling.
- Fit ALL preprocessing on train only, then `transform` val/test. Use `sklearn.Pipeline` so CV re-fits per fold.

## Bias–variance
- Test error ≈ `bias² + variance + irreducible noise`.
- **High bias** (underfit): too simple, high train+val error. Fix: more features, more complex model, less regularization, train longer.
- **High variance** (overfit): memorizes train, low train error / high val error. Fix: more data, regularization, simpler model, feature selection, dropout, bagging, early stopping.
- Sweet spot minimizes val error; increasing complexity trades bias↓ for variance↑.

## Regularization
- **L2 (Ridge)**: penalty `λΣwᵢ²`; shrinks weights smoothly, keeps all features. Closed form `(XᵀX + λI)⁻¹Xᵀy`.
- **L1 (Lasso)**: penalty `λΣ|wᵢ|`; drives weights to exactly 0 → sparse feature selection.
- **Elastic Net**: `λ₁Σ|w| + λ₂Σw²`.
- **Dropout** (NN): randomly zero units w/ prob `p` during training. **Early stopping**: halt when val loss rises. **Data augmentation**, **weight decay** (= L2 in SGD).

## Core algorithms
- **Linear regression**: `ŷ = wᵀx + b`; minimize MSE; solve via normal equation or GD.
- **Logistic regression**: `p = σ(wᵀx+b)`, `σ(z)=1/(1+e⁻ᶻ)`; minimize binary cross-entropy; linear decision boundary; outputs calibrated-ish probabilities.
- **Decision tree**: recursive splits maximizing info gain (entropy) or Gini decrease; interpretable, high variance, prone to overfit → prune / limit `max_depth`, `min_samples_leaf`.
- **Random forest**: bagging of trees + random feature subsets per split; reduces variance; `n_estimators`, `max_features≈√d`. Robust default, little tuning.
- **Gradient boosting** (XGBoost / LightGBM / CatBoost): sequential trees fit to residuals/gradients; strong on tabular. Key: `learning_rate` (0.01–0.3), `n_estimators`, `max_depth` (3–8), `subsample`, `colsample_bytree`, `reg_lambda`. Lower LR + more trees + early stopping.
- **SVM**: maximize margin; hinge loss; kernel trick (RBF `exp(-γ‖x-x'‖²)`, poly) for nonlinearity; `C` (regularization inverse), `γ`. Scale features first.
- **kNN**: predict by `k` nearest (Euclidean/cosine); lazy, no training; sensitive to scale + curse of dimensionality; `k` odd for binary.
- **k-means**: minimize within-cluster SSE; needs `k`, scale features, sensitive to init (use k-means++); assumes spherical clusters. Elbow / silhouette to pick `k`.
- **PCA**: eigen-decomp of covariance / SVD; project onto top components by explained variance; **must standardize first**; linear, unsupervised.
- **Naive Bayes**: `P(y|x) ∝ P(y)∏P(xᵢ|y)`; fast text baseline.

## Feature engineering + scaling
- **Standardize** `(x-μ)/σ` for SVM, kNN, k-means, PCA, linear/logistic w/ regularization, NNs. **Min-max** `[0,1]` for bounded inputs.
- Trees/forests/boosting are **scale-invariant** — no scaling needed.
- Categorical: one-hot (low cardinality), target/ordinal encoding (high cardinality — beware leakage, use CV encoding), embeddings.
- Handle missing: impute (median/mode/model-based) or native NaN handling (LightGBM/XGBoost). Log-transform skewed; bin, interactions, datetime parts.

## Metrics
- **Classification**: accuracy (misleading under imbalance); `precision = TP/(TP+FP)`; `recall = TP/(TP+FN)`; `F1 = 2·P·R/(P+R)`; **ROC-AUC** (rank quality, threshold-free); **PR-AUC** (better for rare positives); log-loss; confusion matrix.
- **Regression**: `MSE`, `RMSE` (same units, penalizes large errors), `MAE` (robust to outliers), `R² = 1 - SS_res/SS_tot`, MAPE.
- Choose by cost: recall for cancer screening, precision for spam, F1 balance, AUC for ranking.

## Cross-validation
- **k-fold** (k=5/10): rotate folds, average metric → robust estimate on small data.
- **Stratified** k-fold preserves class ratios (classification).
- **GroupKFold** when correlated groups (patient/user) must not span folds.
- **TimeSeriesSplit** / walk-forward: train past → test future; never shuffle time series.
- Nested CV for unbiased hyperparameter + model selection.

## Class imbalance
- Resample: SMOTE / oversample minority, undersample majority.
- `class_weight='balanced'` / weighted loss.
- Adjust decision threshold via PR curve; use PR-AUC, F1, balanced accuracy — not raw accuracy.
- Collect more minority data; anomaly framing if extreme.

## Gradient descent + learning rate
- Update `θ ← θ - η∇L(θ)`. **Batch** GD (all data), **SGD** (one sample), **mini-batch** (32–512, standard).
- **LR `η`** most important knob: too high → diverge/oscillate; too low → slow, stuck. Use LR schedules (step, cosine, warmup) or adaptive optimizers (Adam).
- Normalize features so loss surface is well-conditioned (faster convergence).
- Momentum accelerates through ravines; escapes shallow minima.

## Hyperparameter tuning
- **Grid search** (exhaustive, small spaces), **random search** (better for high-dim, few important dims), **Bayesian** (Optuna/Hyperopt — model surrogate), **Hyperband/ASHA** (early-stop bad configs).
- Tune on val / CV only. Log-scale search LR, `C`, `λ`. Fix seed for reproducibility.

## Ensembles
- **Bagging** (bootstrap aggregating): train models on resampled subsets, average/vote → reduces variance (random forest). Parallel, robust.
- **Boosting**: sequential, each model corrects prior errors → reduces bias (AdaBoost reweights misclassified; gradient boosting fits residual gradients). Higher variance, tune carefully.
- **Stacking**: train a meta-model on out-of-fold predictions of diverse base models. Use CV to generate meta-features (avoid leakage).
- **Voting**: hard (majority) or soft (average probabilities). Diverse, decorrelated models help most.

## Learning curves + diagnostics
- Plot train + val error vs training-set size. Converged-high both → high bias (add capacity). Large train–val gap → high variance (more data/regularize).
- Plot metric vs model complexity to find the bias–variance sweet spot.
- Validation curve: metric vs a single hyperparameter.
- Always compare against a **baseline**: majority-class classifier, mean/median regressor, or simple heuristic. A model that can't beat the baseline is useless.

## Curse of dimensionality
- As `d` grows, points become sparse + equidistant → distance-based methods (kNN, k-means, RBF-SVM) degrade; need exponentially more data.
- Mitigate: feature selection (filter by mutual info/χ²; wrapper RFE; embedded L1/tree importance), dimensionality reduction (PCA, UMAP), regularization, domain features.

## Probability calibration
- Raw scores ≠ true probabilities. Trees/boosting/SVM often miscalibrated.
- Calibrate with **Platt scaling** (sigmoid fit) or **isotonic regression** on a held-out set; check with reliability diagram + Brier score / ECE.
- Logistic regression is naturally fairly calibrated.

## Decision thresholds
- Default 0.5 is rarely optimal. Pick threshold from PR/ROC curve by business cost (cost-sensitive), Youden's J, or target precision/recall.
- Multi-class: argmax of softmax; per-class thresholds for imbalance.

## Interpretability
- Global: linear coefficients, tree feature importance (Gini — biased to high-cardinality; prefer **permutation importance**), partial dependence plots.
- Local: **SHAP** (Shapley values, additive, consistent), LIME (local surrogate). Report uncertainty; correlation ≠ causation.

## Workflow / reproducibility
- Fix random seeds; version data + code + configs; log experiments (metrics, params) with MLflow/W&B.
- Pipeline: EDA → clean → split → baseline → feature eng → model → tune (CV) → evaluate on held-out test once → error analysis → monitor drift in production.
- Establish target metric + acceptance bar before modeling; avoid metric-chasing on a leaked test set.

## Pitfalls -> Fix
- **Preprocessing before split** (leakage) -> fit transforms on train fold only; wrap in `Pipeline`.
- **Tuning on test set** -> hold test out entirely; tune on val/CV.
- **Accuracy on imbalanced data** -> use F1/PR-AUC/recall + class weights.
- **Shuffling time series** -> TimeSeriesSplit / chronological split.
- **Unscaled features for SVM/kNN/k-means/PCA** -> standardize.
- **Target leakage feature** (e.g. `total_paid` predicting default) -> audit each feature for future/label info.
- **Duplicate or grouped rows across splits** -> dedupe; GroupKFold.
- **Comparing models on different splits/seeds** -> fix seed, same CV folds.
- **Extrapolation beyond training distribution** -> monitor drift; flag out-of-range inputs.
- **Overfitting hyperparameter search** (too many trials on small val) -> nested CV; regularize.
- **Ignoring baseline** -> always compare to majority-class / mean predictor.
- **Reading feature importance as causation** -> importances are correlational + biased toward high-cardinality; use permutation importance / SHAP.
- **p-hacking metric** across many runs -> pre-register metric; report CV std, not just mean.
