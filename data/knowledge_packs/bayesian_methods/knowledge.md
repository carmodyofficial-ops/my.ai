# Bayesian Methods

Treat unknown parameters as **random variables with distributions**; update beliefs with data. Output is a full **posterior distribution**, not a point estimate.

## Bayes' theorem
```
posterior ∝ likelihood × prior
p(θ|D) = p(D|θ) p(θ) / p(D)      p(D) = ∫ p(D|θ)p(θ) dθ  (evidence/marginal likelihood)
```
- `p(θ)` **prior** (belief before data), `p(D|θ)` **likelihood** (data model), `p(θ|D)` **posterior**, `p(D)` normalizing constant (usually intractable → why we need MCMC/VI).
- Posterior is a compromise between prior and data; as N→∞ likelihood dominates (prior washes out) unless prior is dogmatic (zero mass).

## Priors
- **Informative**: encodes real prior knowledge (e.g. `Normal(μ0, small σ)`); pulls estimates, useful with little data.
- **Weakly informative** (default best practice): regularizes, rules out absurd values, minimal influence with decent N (e.g. `Normal(0, 2.5)` on standardized coefs, `HalfNormal`/`Exponential` on scales).
- **Flat/noninformative/improper**: `Uniform(-∞,∞)` etc.; can be **improper** (doesn't integrate to 1) → may yield improper posterior. Avoid by default.
- **Conjugate**: prior + likelihood give same-family posterior (closed form, no sampling).
  - **Beta–Binomial**: `θ~Beta(a,b)`, `k` successes in `n` → posterior `Beta(a+k, b+n−k)`.
  - **Gamma–Poisson**, **Normal–Normal** (known variance), **Dirichlet–Multinomial**, **Normal-Inverse-Gamma**.
- Prior on the **scale/variance** matters a lot in hierarchical models; use `HalfNormal`/`HalfCauchy`/`Exponential`, not Inverse-Gamma(ε,ε).

## Posterior summaries & vs frequentist
- **Credible interval**: 95% CrI = interval containing 95% of posterior mass. Direct statement: "95% probability θ is in here **given the data + prior**." (Frequentist **confidence** interval: 95% of such intervals cover θ over repeated sampling — **not** a probability about this θ.)
- **HDI** (highest density interval) vs **equal-tailed** (2.5/97.5 quantiles); HDI is narrowest, better for skewed posteriors.
- Point summaries: posterior mean/median/mode (MAP). **MAP** = posterior mode = penalized MLE (ridge = Normal prior, lasso = Laplace prior).
- Bayesian mindset: probability = degree of belief; parameters random, data fixed. Frequentist: parameters fixed, data random; p-values, CIs, no priors.

## Computation
- **MCMC**: sample from posterior when no closed form.
  - **Metropolis–Hastings**: propose θ', accept w.p. `min(1, [p(θ'|D)q(θ|θ')]/[p(θ|D)q(θ'|θ)])`. Simple, tune step size (target accept ~23–50%).
  - **Gibbs**: sample each parameter from its full conditional; good with conjugate conditionals; can mix slowly under high correlation.
  - **HMC / NUTS** (Hamiltonian Monte Carlo, No-U-Turn): use gradients of log-posterior → efficient in high dimensions, low autocorrelation. Default in Stan/PyMC/NumPyro. Needs differentiable model (continuous params; marginalize discretes).
- **Variational Inference (VI)**: approximate posterior with a simpler family `q(θ)`; maximize ELBO (minimize KL). Fast + scalable, but **underestimates variance** and misses multimodality (ADVI, mean-field). Use when MCMC too slow / big data.
- **PPLs**: **Stan** (HMC/NUTS, its own language), **PyMC** (Python, PyTensor backend), **NumPyro** (JAX, fast NUTS), **Pyro**, **Turing.jl**, **brms** (R formula → Stan). Specify priors + likelihood; engine samples.

## Hierarchical / multilevel models
- Parameters share a common prior whose hyperparameters are also learned: `y_ig ~ f(θ_g)`, `θ_g ~ Normal(μ, τ)`, `μ,τ ~ hyperpriors`.
- **Partial pooling** (shrinkage): group estimates borrow strength → shrink toward global mean, most for small/noisy groups. Between no-pooling (each group alone) and complete-pooling (ignore groups). Ideal for repeated/grouped/nested data, many small groups, multi-arm experiments.
- Automatically handles multiple comparisons via shrinkage.

## Bayesian A/B testing
- Model conversions `Beta–Binomial` per arm; posterior over each rate; compute `P(θ_B > θ_A | data)` and **expected loss / uplift** distribution directly from posterior draws.
- No fixed sample size / peeking penalty in the frequentist sense — decisions via posterior probability + expected loss; still define a stopping rule + prior to avoid bias.

## Model checking & comparison
- **Prior predictive check**: simulate data from prior → are simulated outcomes plausible? Reveals absurd priors before seeing data.
- **Posterior predictive check (PPC)**: simulate replicated data from posterior, compare to observed (test statistics, overlaid densities) → does the model reproduce the data?
- **Comparison**: **WAIC** and **PSIS-LOO** (leave-one-out CV via Pareto-smoothed importance sampling) estimate out-of-sample predictive accuracy (ELPD); prefer LOO, check Pareto-k diagnostics. **Bayes factors** (`p(D|M1)/p(D|M2)`) — extremely sensitive to priors, hard to compute; use with care. **Marginal likelihood** for model evidence.

## Convergence diagnostics
- **R̂ (Gelman–Rubin)**: compares between/within-chain variance; want **R̂ < 1.01**. >1.01 → not converged.
- **ESS** (effective sample size): bulk-ESS + tail-ESS; want ≥ ~400. Low ESS → high autocorrelation, unreliable summaries.
- **Trace plots**: chains should overlap ("fuzzy caterpillar"), no trends. **Divergences** (HMC/NUTS): even a few indicate biased geometry → reparameterize / raise `target_accept`. Run ≥4 chains from dispersed inits.

## Minimal PyMC example
```python
import pymc as pm
with pm.Model() as m:
    theta = pm.Beta("theta", alpha=1, beta=1)          # prior
    y = pm.Binomial("y", n=n, p=theta, observed=k)     # likelihood
    idata = pm.sample(2000, tune=1000, chains=4,        # NUTS
                      target_accept=0.9)
    pm.sample_posterior_predictive(idata, extend_inferencedata=True)
az.summary(idata)         # mean, sd, hdi, r_hat, ess_bulk, ess_tail
az.loo(idata)             # PSIS-LOO for comparison
```
- Workflow: prior predictive → fit → check R̂/ESS/divergences → posterior predictive → compare (LOO) → iterate ("Bayesian workflow", Gelman et al.).

## Decision-making with posteriors
- Propagate full posterior into downstream decisions: compute `P(hypothesis | data)`, expected value/loss over posterior draws, **posterior predictive** for new-data forecasts (integrates parameter uncertainty, unlike a plug-in point estimate).
- Regularization view: priors = principled regularizers; hierarchical shrinkage = adaptive, data-driven regularization strength.

## Pitfalls -> Fix
- **Overly strong/wrong prior** dominates data, biases posterior. Fix: prior predictive checks; use weakly-informative defaults; sensitivity analysis across priors.
- **Improper/flat priors** → improper or pathological posterior, non-identifiability. Fix: proper weakly-informative priors, especially on variance/scale.
- **Non-convergence** (R̂ > 1.01, non-overlapping chains). Fix: more/longer chains + warmup, reparameterize, better priors, check model identifiability — do **not** report unconverged results.
- **Divergent transitions** in NUTS (funnel geometry in hierarchical models). Fix: **non-centered parameterization** (`θ = μ + τ·z`, `z~Normal(0,1)`), increase `target_accept` (0.9→0.99), reparameterize scales.
- **Low ESS / high autocorrelation** → unstable estimates. Fix: HMC/NUTS over Metropolis/Gibbs, reparameterize, thin only if needed, more samples.
- **Too few samples / no warmup** → unreliable tails/CrIs. Fix: adequate warmup (discard), enough post-warmup draws (thousands), check tail-ESS.
- **Confusing credible with confidence interval** / over-interpreting. Fix: state prior dependence; CrI is a belief statement, not frequentist coverage.
- **VI's underestimated uncertainty** taken as exact. Fix: validate against MCMC on a subset; report VI approximates and shrinks variance/misses modes.
- **Ignoring multimodality** (single chain stuck in one mode). Fix: multiple dispersed chains, tempering; inspect trace/pairs.
- **Computational cost** for big data/complex models. Fix: NumPyro/JAX + GPU, VI, subsampling/mini-batch VI, conjugacy/marginalization, reduce hierarchy.
- **Comparing models by in-sample fit / likelihood only** → overfitting. Fix: LOO/WAIC (out-of-sample ELPD), PPCs; check Pareto-k.
- **Point-estimate thinking** (report only posterior mean, drop the distribution). Fix: report full posterior / CrI / predictive distribution; propagate uncertainty downstream.
- **Bayes factors reported as prior-independent**. Fix: acknowledge extreme prior sensitivity; prefer LOO for prediction-oriented comparison.
```
