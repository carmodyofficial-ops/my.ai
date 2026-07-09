# Quantitative Finance Foundations

Educational reference (concepts/methods/formulas). Not financial advice.

## Returns & compounding
- Arithmetic (simple) return: `r_t = P_t/P_{t-1} - 1`. Aggregates across assets at a point in time (portfolio return = weighted mean of arithmetic returns).
- Log (continuously compounded) return: `l_t = ln(P_t/P_{t-1}) = ln(1+r_t)`. Aggregates additively across time: `l_{0→n} = Σ l_t`. Preferred for time-series modeling/stats.
- Convert: `r = e^l - 1`. For small r, `l ≈ r - r²/2`; log return always ≤ arithmetic.
- Multi-period (geometric): `1+R = Π(1+r_t)`; CAGR = `(P_end/P_start)^(1/yrs) - 1`.
- Geometric mean ≤ arithmetic mean; gap ≈ `σ²/2` (volatility drag). Realized compound growth ≈ `μ - σ²/2`.
- Annualization: return `μ_ann = μ_period × k`; vol `σ_ann = σ_period × √k` (k = periods/yr: 252 trading days, 12 months, 52 weeks). √-time scaling assumes i.i.d. returns.

## Arithmetic of loss (asymmetry)
- Recovery from drawdown d needs gain `g = d/(1-d)`: -10%→+11.1%, -20%→+25%, -50%→+100%, -90%→+900%.
- +50% then -50% ends at 0.75× (−25%), not flat. Losses compound harder than gains — controlling downside/variance drives geometric growth.

## Risk metrics
- Volatility: `σ = std(returns)`, annualized `σ√k`. Dispersion, not loss.
- Downside deviation: std of returns below a threshold (MAR); used in Sortino.
- Sharpe: `(E[r] - r_f)/σ`, annualized `(μ-r_f)√k/σ` on periodic returns. Heuristic: >1 good, >2 strong, >3 suspect (overfit/leakage). Sensitive to non-normality.
- Sortino: `(E[r] - MAR)/σ_downside` — penalizes only downside; rewards positive skew.
- Calmar: `CAGR / |MaxDrawdown|` (usually 3-yr). MAR ratio is similar.
- Information ratio: `(r_p - r_bench)/tracking_error` (active return per unit active risk).
- Max drawdown (MDD): largest peak-to-trough decline `min_t(P_t/max_{s≤t}P_s - 1)`. Report drawdown duration / time-to-recovery too.
- Beta: `Cov(r_i, r_m)/Var(r_m)` — systematic market sensitivity.

## VaR / CVaR
- VaR_α: loss not exceeded with prob α over horizon h (95% 1-day VaR = 5th-percentile loss). Methods: historical (empirical quantile), parametric Gaussian (`VaR = -(μ + z_α σ)`, z_95=1.645, z_99=2.326), Monte Carlo.
- VaR is NOT coherent (not sub-additive); ignores the tail beyond the quantile.
- CVaR / Expected Shortfall: `E[loss | loss > VaR_α]` — coherent, captures tail severity. Preferred for fat-tailed risk.

## Distributions & fat tails
- Returns are leptokurtic (fat-tailed) and often left-skewed; Gaussian understates tail risk.
- Skewness: 3rd standardized moment; negative = crash-prone left tail. Kurtosis: 4th moment; normal = 3, excess = kurt−3; returns commonly 5–30+.
- Volatility clustering (ARCH/GARCH): large moves follow large moves; σ is time-varying and autocorrelated even when returns aren't.
- Tests: Jarque–Bera (normality), Ljung–Box (autocorrelation), ADF/KPSS (stationarity).

## Correlation vs cointegration
- Correlation: co-movement of returns `ρ = Cov/(σ_xσ_y) ∈ [−1,1]`; unstable, spikes toward 1 in crises (diversification fails when most needed).
- Cointegration: two I(1) price series whose linear combination is stationary I(0) — a mean-reverting spread; basis of pairs/stat-arb. Test: Engle–Granger (residual ADF) or Johansen. Correlation ≠ cointegration: series can be highly correlated yet drift apart (no tradable spread), or cointegrated with low return correlation.

## Portfolio math (mean–variance)
- Return `μ_p = wᵀμ`. Variance `σ_p² = wᵀΣw` (Σ = covariance matrix).
- Two-asset: `σ_p² = w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρσ₁σ₂`. ρ<1 → diversification cuts σ below the weighted average.
- Efficient frontier: min σ per target μ. Tangency portfolio maximizes Sharpe; Capital Market Line = risk-free + tangency.
- Diversification: idiosyncratic risk → 0 as N grows; systematic (market) risk remains. Marginal benefit decays fast (~15–30 uncorrelated names capture most).
- Risk parity: weight so each asset contributes equal risk (`w_i ∝ 1/σ_i` in simple form), not equal capital.
- Kelly: growth-optimal fraction `f* = μ/σ²` (continuous) or `edge/odds`; full Kelly is high-variance — use fractional (¼–½) Kelly.

## Factor models
- CAPM: `E[r_i] - r_f = β_i(E[r_m] - r_f)`. Single (market) factor; α = intercept = excess return unexplained by β.
- Fama–French 3-factor: market + SMB (size) + HML (value); 5-factor adds RMW (profitability), CMA (investment); Carhart adds MOM (momentum).
- Multi-factor: `r_i = α + Σ β_k F_k + ε`. Regress returns on factor returns; α = edge net of known factors. Much apparent alpha is disguised factor beta.

## Statistics of edge
- SE of mean return `≈ σ/√N`. Strategy t-stat `≈ Sharpe × √(years)`. SR=1 needs ~4 yrs for t≈2.
- Deflated / probabilistic Sharpe: adjust for number of trials tested (multiple-testing / selection bias).

## Pitfalls → Fix
- Averaging log returns then treating as arithmetic → arithmetic for cross-sectional/portfolio aggregation, log for time aggregation.
- Reporting arithmetic mean as "expected growth" → use geometric/CAGR; subtract drag `σ²/2`.
- √-time annualizing autocorrelated/illiquid returns → understates risk; correct for serial correlation.
- Sharpe on non-normal returns → add Sortino, CVaR, MDD; high Sharpe + large negative skew (short-vol) hides tail risk.
- Gaussian VaR on fat tails → use historical or fat-tailed models; prefer CVaR.
- Trusting correlation for hedging → it decays/inverts in stress; test cointegration for spread trades; Σ is unstable and ill-conditioned.
- Mean-variance optimizer output → hypersensitive to μ estimates ("error maximization"); shrink covariance (Ledoit–Wolf), constrain weights, or use risk parity / equal-weight.
- In-sample Sharpe as live expectation → discount for costs, slippage, capacity, overfitting; use walk-forward / out-of-sample.
- Edge from small N → require adequate t-stat; correct for multiple testing (data snooping).
- Survivorship / look-ahead bias → use point-in-time, delisting-inclusive data.
- Confusing ex-ante expectation with ex-post realization → a good decision can have a bad outcome; judge process, not a single draw.
- Full Kelly / max leverage → path risk of ruin; size fractionally, cap drawdown.

## Leverage, costs, capacity, regime
- Leverage L scales both return and vol: `μ_L = L·μ`, `σ_L = L·σ` (Sharpe unchanged), but drawdowns and ruin risk scale nonlinearly; geometric growth `L·μ − L²σ²/2` is maximized at `L* = μ/σ²` (Kelly) then falls — over-leverage destroys compounding.
- Margin: initial vs maintenance; a margin call forces liquidation at the worst time (procyclical). Financing cost reduces net carry.
- Transaction costs: net return `= gross − (spread/2 + fees + impact + borrow)` per turnover. High-turnover edges are cost-fragile; measure turnover-adjusted net Sharpe.
- Capacity: max AUM before impact erodes edge to zero; net alpha declines with size (square-root impact). A backtest ignoring capacity overstates a large-size strategy.
- Regime dependence: μ, σ, ρ are non-stationary; parameters estimated in one regime fail in another. Use rolling/expanding windows, regime models, and out-of-sample validation.

## Worked example
- $100 → −50% → $50 → needs +100% to recover. A strategy with μ=8%/yr arithmetic, σ=20% has geometric growth ≈ `0.08 − 0.20²/2 = 0.06` (6%/yr) — the 2% gap is volatility drag.

## Deterministic-math discipline
- Use exact tools for compounding, drawdown, VaR quantiles, and matrix ops — never eyeball nonlinear/geometric quantities.
- State assumptions explicitly (horizon, i.i.d., distribution, costs); distinguish ex-ante expectation from ex-post realization in every claim.
