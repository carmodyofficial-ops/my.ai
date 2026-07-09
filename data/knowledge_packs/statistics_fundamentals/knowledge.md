# Statistics Fundamentals

## Descriptive statistics
- **Mean** `x̄ = Σxᵢ/n` — sensitive to outliers. **Median** = 50th percentile — robust. **Mode** = most frequent.
- Skew right (long right tail): `mean > median`. Skew left: `mean < median`. Report median for skewed/income data.
- **Variance** (sample) `s² = Σ(xᵢ−x̄)²/(n−1)` — `n−1` = Bessel's correction (unbiased). Population uses `/n`.
- **Std** `s = √s²` — same units as data. **CV** `= s/x̄` — unitless spread comparison.
- **IQR** `= Q3 − Q1`; outlier fence `Q1 − 1.5·IQR`, `Q3 + 1.5·IQR`. Robust spread.
- **Std vs SE**: std describes data spread; standard error `SE = s/√n` describes precision of the *mean estimate*. Do not confuse — SE shrinks with `n`, std does not.

## Distributions
- **Normal** `N(μ,σ²)`: symmetric, 68/95/99.7 within 1/2/3σ. Sum of many small effects → normal (CLT).
- **Binomial** `B(n,p)`: # successes in `n` iid trials; `mean=np`, `var=np(1−p)`. Use for conversion counts.
- **Poisson** `Pois(λ)`: rare-event counts per interval; `mean=var=λ`. Approximates binomial when `n` large, `p` small.
- **Bernoulli**: single 0/1 trial, `p`. **Exponential**: waiting time between Poisson events. **Uniform**, **Log-normal** (multiplicative processes, right-skewed).
- Check normality: Q-Q plot (best visual), Shapiro-Wilk (`n<5000`), not just histogram.

## CLT, sampling, standard error
- **CLT**: sampling distribution of the mean → normal as `n→∞` regardless of population shape; rule of thumb `n≥30` (more if heavy-skewed/heavy-tailed).
- `SE_mean = σ/√n` (use `s` when σ unknown). Halving SE needs 4× the data.
- `SE_proportion = √(p(1−p)/n)`. Larger samples → tighter estimates, diminishing returns.

## Confidence intervals
- 95% CI for mean: `x̄ ± t*·SE`, `t*` from t-dist with `df=n−1` (≈1.96 for large n). Use z only if σ known.
- **Interpretation**: 95% of such intervals (over repeated sampling) contain the true parameter. NOT "95% probability the parameter is in this interval" (frequentist).
- Proportion CI (Wald) `p̂ ± 1.96·√(p̂(1−p̂)/n)`; use **Wilson/Agresti-Coull** for small `n` or extreme `p̂`.
- Wider CI = less certain (small `n`, high variance). CI excluding null value ≈ significant at that α.

## Hypothesis testing
- **H₀** (null, no effect) vs **H₁** (alternative). Assume H₀, compute test statistic + **p-value** = P(data this extreme or more | H₀ true).
- Reject H₀ if `p < α` (typically 0.05). **p is NOT** P(H₀ true) nor effect size nor P(replication).
- **Type I (α)**: false positive — reject true H₀. **Type II (β)**: false negative — fail to reject false H₀.
- **Power = 1−β** (aim ≥0.80): P(detect a real effect). Increases with larger effect, larger `n`, higher α, lower variance.
- One-tailed (directional) vs two-tailed (default; halves each tail). Pre-register direction to avoid cheating.

## Common tests (pick by data + question)
| Question | Test | Notes |
|---|---|---|
| 1 mean vs value | one-sample t | normal-ish |
| 2 independent means | two-sample (Welch) t | Welch = unequal var, default |
| paired/before-after means | paired t | within-subject |
| 2 medians / non-normal | Mann-Whitney U | rank-based |
| paired non-normal | Wilcoxon signed-rank | |
| ≥3 group means | one-way ANOVA (F) | + Tukey HSD post-hoc |
| ≥3 non-normal | Kruskal-Wallis | |
| categorical association | chi-square / Fisher exact | Fisher when expected cell <5 |
| 2 proportions | z-test / chi-square | |
- Assumptions: t/ANOVA → independence, normal residuals, homogeneity of variance (Levene). Violated → use non-parametric or Welch.

## Correlation vs causation
- **Pearson r** ∈ [−1,1]: *linear* association; sensitive to outliers, requires normal-ish. **Spearman ρ**: rank/monotonic, robust. **Kendall τ**: small samples/ties.
- `r² ` = shared variance fraction. `r=0` ≠ independent (can be nonlinear — always plot).
- Correlation ≠ causation: confounders, reverse causation, selection bias, coincidence. Causation needs RCT, natural experiment, or causal inference (DAGs, IV, diff-in-diff).

## Regression (OLS linear)
- `ŷ = β₀ + β₁x₁ + … + βₖxₖ`; minimize `Σ(yᵢ−ŷᵢ)²`.
- **Coefficient** `βⱼ` = expected Δy per unit Δxⱼ, *holding others fixed*. Check p-value + CI per coef.
- **R²** = fraction of variance explained; always ↑ with more predictors → use **adjusted R²** for model comparison.
- **Assumptions (LINE)**: Linearity, Independence of errors, Normality of residuals, Equal variance (homoscedasticity). Also low **multicollinearity** (VIF < 5–10).
- Diagnostics: residual-vs-fitted (patterns → nonlinearity/heteroscedasticity), Q-Q plot, Cook's distance (influential points).
- Fixes: transform (log), add interactions/polynomials, robust SE (heteroscedasticity), regularization (ridge/lasso for collinearity).

## Bayesian vs frequentist
- **Frequentist**: parameters fixed, data random; p-values + CIs; no prior. **Bayesian**: parameters have distributions; `posterior ∝ likelihood × prior`; gives credible intervals + direct P(hypothesis).
- Bayesian 95% **credible interval** = "95% probability parameter in range" (the intuitive reading CIs lack).
- Use Bayesian for prior knowledge, small samples, sequential updating, decision-theoretic outputs. Frequentist default for regulated/pre-registered work.

## Multiple comparisons + effect size
- Testing `m` hypotheses at α inflates false positives: `P(≥1 FP) = 1−(1−α)^m`. 20 tests at 0.05 → ~64% chance of a false positive.
- **Bonferroni**: use `α/m` (conservative, controls FWER). **Holm** (stepwise, more powerful). **Benjamini-Hochberg**: controls FDR (expected false-discovery proportion) — better for many exploratory tests.
- **Effect size** conveys magnitude (p only conveys evidence-of-existence): **Cohen's d** = `(x̄₁−x̄₂)/s_pooled` (0.2 small, 0.5 med, 0.8 large); **r**; **η²**/**Cohen's f** (ANOVA); **odds ratio**/**risk ratio** (categorical). Always report effect size + CI alongside p.

## Probability + Bayes rule
- **Bayes**: `P(A|B) = P(B|A)·P(A) / P(B)`. Diagnostic: `P(disease|+) = sens·prev / (sens·prev + (1−spec)·(1−prev))`.
- Rare disease (prev=1%), test sens=99%, spec=95% → `P(disease|+) ≈ 0.99·0.01 / (0.99·0.01 + 0.05·0.99) ≈ 17%`. Most positives are false — base rate dominates.
- Independence: `P(A∩B)=P(A)P(B)`. Mutually exclusive: `P(A∪B)=P(A)+P(B)`. Conditional: `P(A|B)=P(A∩B)/P(B)`.
- **Odds ratio** `OR = (a/b)/(c/d)` from 2×2 table; **relative risk** `RR = (a/(a+b))/(c/(c+d))`. OR overstates RR when outcome common.

## Resampling + bootstrap
- **Bootstrap**: resample data with replacement `B` times (≥1000–10000), recompute statistic → empirical sampling distribution. CI via 2.5/97.5 percentiles. No distributional assumptions; works for medians, ratios, any statistic.
- **Permutation test**: shuffle group labels many times to build the null distribution of a difference → exact p-value; robust when parametric assumptions fail.
- **Jackknife**: leave-one-out resampling to estimate bias/variance. Cross-validation is resampling applied to model error.

## Degrees of freedom + assumptions checks
- `df` = # independent pieces of info; t-test `df=n−1`, two-sample Welch uses Satterthwaite `df`, chi-square `df=(r−1)(c−1)`, regression residual `df=n−k−1`.
- Check before parametric tests: independence (design), normality (Q-Q, Shapiro), equal variance (Levene/Bartlett), linearity (residual plots). Violated → transform, Welch, robust SE, or non-parametric.

## Categorical + count data
- **Chi-square goodness-of-fit**: observed vs expected frequencies, `χ² = Σ(O−E)²/E`. Needs expected cell counts ≥5; else Fisher exact.
- **Chi-square independence**: association in an `r×c` contingency table. Effect size via **Cramér's V**.
- Count/rate models → Poisson or negative binomial regression (overdispersion when `var > mean` → use NB).

## Pitfalls -> Fix
- **p-hacking** (try tests/subgroups/cutoffs until p<0.05) -> pre-register hypotheses + analysis; report all tests; correct for multiplicity.
- **"p=0.06 means no effect"** -> absence of significance ≠ evidence of absence; report effect size + CI; may be underpowered.
- **"p<0.05 means important/large"** -> significance ≠ magnitude; huge `n` makes trivial effects significant; report effect size.
- **Ignoring assumptions** (using t on skewed/heteroscedastic data) -> plot residuals; use Welch/non-parametric/transform.
- **Confusing SE and SD** in error bars -> label which; SE for mean precision, SD for spread, CI for inference.
- **Correlation → causation** -> require experiment or causal design; list confounders.
- **Base-rate neglect** (P(disease|+) ≠ test sensitivity) -> apply Bayes; rare conditions → many false positives even with accurate tests.
- **Simpson's paradox** (aggregate reverses subgroups) -> check confounders; stratify before pooling.
- **Peeking / optional stopping** in fixed tests -> inflates Type I; use sequential methods or fix `n` upfront.
- **Overfitting with too many predictors** (R² inflation) -> adjusted R², cross-validation, out-of-sample check.
- **Truncated/selected samples** (survivorship bias) -> define population + sampling frame explicitly.
- **Outliers distorting mean/variance/r** -> report median/IQR/Spearman; investigate before dropping; never delete silently.
- **Multiple-testing in dashboards/monitoring** -> BH-FDR control; treat alerts as exploratory.
- **Reporting mean of skewed data** -> use median + IQR; log-transform.
