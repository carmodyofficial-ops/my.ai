# Time Series Econometrics
## Stationarity
- Weak stationarity: constant mean, variance, autocovariance depends only on lag. Most models require it.
- **ADF** (null = unit root / non-stationary): reject (p<0.05) ⇒ stationary. **KPSS** (null = stationary): opposite framing — use both; ADF-reject + KPSS-fail-to-reject = confident stationary. Conflicting = borderline/fractional.
- Fixes: difference (Δ = I(1)→I(0)), log to stabilize variance, de-trend. Prices are typically I(1); **returns** ≈ stationary — model returns, not levels.
## ACF/PACF & ARIMA identification
- **ACF** cuts off at lag q ⇒ MA(q); **PACF** cuts off at lag p ⇒ AR(p); both decay ⇒ ARMA. ARIMA(p,d,q): d = differences to stationarity.
- Select by **AIC/BIC** (BIC penalizes params harder → parsimony). Check residuals: **Ljung-Box** on residuals should be white noise; residual ACF flat.
- Don't over-difference (introduces spurious negative MA autocorrelation, inflates variance). Confirm d with unit-root tests, not eyeballing.
## Volatility: ARCH/GARCH
- Returns show **volatility clustering** (calm/turbulent regimes) and fat tails — mean models miss this. **ARCH(q)** / **GARCH(p,q)**: σ²_t = ω + α·ε²_{t−1} + β·σ²_{t−1}. α+β near 1 = high persistence; α+β≥1 ⇒ IGARCH (non-stationary vol).
- **EGARCH/GJR-GARCH** capture leverage/asymmetry (down moves raise vol more). Fit on residuals of the mean model; use Student-t innovations for fat tails.
## Cointegration & pairs
- Two I(1) series are **cointegrated** if a linear combo is I(0) — they share a stochastic trend and mean-revert. Basis for **pairs/stat-arb**.
- **Engle-Granger**: regress y on x, ADF-test the residuals for stationarity (2-var only). **Johansen**: VECM-based, tests cointegration rank for ≥2 series (trace/max-eigen). Estimate hedge ratio from the cointegrating vector; trade the spread's z-score with mean-reversion (half-life via Ornstein-Uhlenbeck).
- Cointegration ≠ correlation. Relationships break — monitor for regime change; recheck the spread's stationarity out-of-sample.
## Regime switching & structural breaks
- **Markov-switching** models (Hamilton): parameters (mean/vol) switch between hidden states with transition probabilities. Captures bull/bear, low/high-vol regimes. Beware overfitting states; more states almost always fit in-sample better — validate OOS.
- **Structural breaks**: parameters shift at unknown dates (**Chow** test at a known break, **Bai-Perron** for multiple unknown breaks, CUSUM for drift). An unmodeled break masquerades as a unit root or as spurious persistence. Re-estimate after regime shifts rather than pooling across them.
- Rolling/expanding estimates and **Kalman filters** let coefficients (e.g. a hedge ratio or beta) evolve over time instead of assuming constancy.
## Returns modeling essentials
- Model **log returns** `r_t = ln(P_t/P_{t−1})`: additive over time, roughly stationary, symmetric-ish. Prices are I(1) and near a random walk — don't regress price-on-price.
- Stylized facts to respect: near-zero mean autocorrelation in returns (weak-form efficiency) but strong autocorrelation in **|returns|/returns²** (vol clustering), fat tails (excess kurtosis), negative skew, leverage effect, and aggregational Gaussianity (tails thin at longer horizons).
## Diagnostics & tests
- Residual autocorrelation: **Ljung-Box / Breusch-Godfrey**. Heteroskedasticity: **ARCH-LM test**, Breusch-Pagan, White. Normality: Jarque-Bera (financial returns fail it — fat tails/skew are the rule).
- Autocorrelation-robust inference: use **Newey-West (HAC)** standard errors when errors are serially correlated/heteroskedastic, else t-stats are overstated.
- **Granger causality** tests predictive precedence, not true causation; sensitive to lag choice and omitted variables.
## Multivariate & memory
- **VAR** for jointly endogenous stationary series (impulse responses, variance decomposition); **VECM** = VAR on differences + error-correction term when cointegrated (don't difference away the long-run relation).
- Long memory: **fractional integration (ARFIMA, d∈(0,0.5))** — slowly decaying ACF between I(0) and I(1); differencing fully would overdifference.
## Validation for time series
- **Never random K-fold** — it leaks future into past. Use **walk-forward / expanding or rolling-window** with a **purge + embargo** gap between train and test to kill leakage from overlapping labels/features.
- Report true **out-of-sample**; account for **multiple testing** (Bonferroni, or deflated/PBO Sharpe) when many strategies/params were tried.
- Backtest overfitting: **PBO** (probability of backtest overfitting) and **deflated Sharpe** discount for the number of trials. Combinatorial purged CV gives a distribution of OOS performance, not one path.
- Enough data: parameter count and regime coverage matter more than raw length — a model unseen in a crisis regime is untested for one.
## Forecasting & evaluation
- Baselines first: **random walk / naive** (tomorrow = today) is brutally hard to beat for prices — beat it before claiming skill. **Drift** and **seasonal-naive** for trending/seasonal series.
- Errors: **RMSE/MAE** (scale-dependent), **MAPE** (breaks near zero), **MASE** (scaled to naive). For trading, evaluate directional accuracy and P&L, not just point error.
- Prediction intervals matter more than point forecasts; report them and check coverage. Widening intervals with horizon is correct, not a flaw.
- Seasonality/decomposition: **STL** (trend + seasonal + remainder); **SARIMA** for seasonal AR/MA; don't confuse deterministic seasonality with a unit root.
## Gotchas -> Fix
- **Spurious regression**: two independent I(1) trends give high R² and t-stats that are meaningless. Fix: difference to stationarity, or verify genuine cointegration; check **Durbin-Watson ≪ 2** (residual autocorrelation) as the tell.
- **Overdifferencing**: over-flattens, injects negative MA structure, inflates variance — difference only to reach stationarity (usually d=1).
- **Look-ahead in features**: rolling stats/normalization using future data, full-sample scaling, restated fundamentals, same-bar signal→fill. Compute features causally, fit scalers on train only.
- **Non-stationary inputs to OLS/ML**: model learns the trend, fails live. Use returns/differences or stationary transforms.
- **Ignoring vol clustering**: constant-variance assumptions understate risk in turbulence — model σ_t with GARCH; don't annualize a calm-window σ.
- **Cointegration assumed permanent**: structural breaks end the relationship — re-test rolling; stop the pair when the spread stops mean-reverting.
- **P-hacking / data snooping**: testing many lags/params/universes until significant. Pre-register, hold out, adjust for the number of trials, prefer OOS confirmation.
- **Random CV on time series**: leaks and overstates skill. Walk-forward with purge/embargo only.
