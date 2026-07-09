# Backtesting & Strategy Validation

Educational quant reference — concepts and method, not financial advice.

## The goal
- A backtest **estimates out-of-sample (OOS) performance**; it is a hypothesis test, not a profit promise. Past = one sample path.
- Default prior: **the strategy is overfit until proven otherwise.** The reported in-sample best is an upward-biased estimate.
- Validate the *process* (does an edge survive unseen data, real costs, regime change?), not the single equity curve.

## Data splits
- **In-sample (IS):** fit/optimize here. **Out-of-sample (OOS):** untouched, scored once — every peek burns it.
- Three-way: **train** (fit) / **validation** (tune & select) / **test** (final, touched once).
- Respect time order: **no random shuffling, no plain K-fold across the time axis** (leaks future into past).

## Walk-forward analysis (time-series gold standard)
- Roll a window: re-optimize on IS, forward-test the next **unseen** window, step, repeat. Stitch OOS segments into one continuous equity curve.
- **Anchored** (growing IS from a fixed start) vs **rolling** (fixed-length IS that slides).
- Yields many independent OOS windows → tests parameter *stability* over time, not just one lucky split. Efficiency ratio = walk-forward return / IS return.

## Cross-validation for time series (purged & embargoed)
- Standard k-fold leaks because labels/features **overlap in time**. Fixes (López de Prado):
  - **Purging:** drop training samples whose label window overlaps the test window.
  - **Embargo:** additionally remove a gap of h bars *after* each test block so serially-correlated info doesn't bleed back.
  - **Combinatorial purged CV (CPCV):** many train/test path combinations → a distribution of OOS curves, not one.

## Transaction costs, slippage, realistic fills
- Model every cost or the backtest lies: **commissions, bid-ask spread, slippage, market impact** (size moves price), **funding** (perps), **borrow** (shorts), latency/queue position.
- **Fill at next-bar open with the spread crossed**, not the magic close/mid of the signal bar.
- Assume **taker** unless you can prove queue priority; market impact grows with size/ADV (√-impact rule of thumb).
- **Stress-test costs by 2×**; many edges are entirely inside the spread and vanish. Avg-trade PnL must clear round-trip cost.

## Biases to avoid
- **Look-ahead:** using future or same-bar-close data to trade that bar. Fix: **lag signals one bar**, trade next open; point-in-time fundamentals (as-reported, not restated).
- **Survivorship:** testing only currently-listed names inflates returns. Fix: **point-in-time universe** incl. delisted/bankrupt/renamed/merged.
- **Data-snooping / p-hacking:** try 1000 variants, one wins by luck. Fix: fewer tests, pre-register, multiple-testing correction (Bonferroni, **deflated Sharpe**), confirm OOS.
- **Overfitting:** too many params memorize noise. Fix: minimize params, prefer simple/robust, regularize, penalize complexity, want a parameter *plateau*.

## Metrics (define precisely)
- **CAGR** = annualized geometric return. **Sharpe** = mean excess return / stdev, annualized (`×√periods`). **Sortino** = downside deviation only. **Calmar** = CAGR / |maxDD|.
- **Max drawdown** (+ duration); **profit factor** = gross profit/gross loss; **expectancy** = per-trade EV in R; **# trades** (need ~100+ for any significance).
- **Deflated Sharpe Ratio (DSR):** adjusts observed Sharpe down for **number of trials tested**, non-normal returns (skew/kurtosis), and sample length → probability the true Sharpe > 0. Kills "I tried 500 configs, best Sharpe 2.5."
- **Probability of Backtest Overfitting (PBO):** via combinatorial splits, the fraction of the time the IS-best config underperforms the median OOS. **High PBO ⇒ selection is noise.**
- Sharpe is inflated by autocorrelation, non-normality, and short samples — never rank on Sharpe alone.

## Statistical significance
- More trades = more evidence. Rough standard error of an annualized Sharpe over `n` years: `SE ≈ √((1 + Sharpe²/2)/n)` — a Sharpe of 1 over 2 years is **not** significantly positive.
- t-stat of mean trade return ≈ `expectancy / (std_trade/√N)`; want |t| well above the trials-adjusted threshold, not just >2.
- Non-normal returns (fat tails, skew) make naïve significance tests optimistic; prefer bootstrap confidence intervals.

## Monte Carlo / bootstrap
- **Resample or shuffle trade order** → distribution of terminal returns & drawdowns; report the **5th percentile / worst path**, not the mean.
- **Block bootstrap** preserves serial correlation (shuffling single bars destroys it). Randomize entry timing / skip trades to test fragility.
- Confidence bands on the equity curve; a strategy whose edge lives in 2–3 outlier trades will show a fat left tail.

## Regime robustness
- Test across **multiple assets, markets, and regimes**: bull/bear/chop, vol spikes, 2008/2020/2022. An edge tied to one asset or one year is not an edge.
- Report per-regime metrics; a filter (ADX/vol) that only works because it dodged one crash is curve-fit.

## Paper-to-live divergence
- Live underperforms backtest via: **real latency, partial fills, queue position, adverse selection, slippage, data revisions, and shrinking alpha** as others trade it.
- **Forward/paper test on live data first**; compare paper fills to backtest assumptions before risking capital. Track live-vs-backtest tracking error as an ongoing monitor.

## Red flags
- Sharpe > 3 for a retail strategy; suspiciously smooth (straight-line) equity curve.
- Very few trades; performance hinges on one asset/one year/one trade.
- Params tuned to the exact test window; no cost model; **in-sample-only** reporting.
- Results vanish OOS or in walk-forward; huge gap between IS and OOS metrics.

## Pitfalls → Fix
- **Optimizing on the test set** → touch test once; select on validation; report OOS.
- **Random k-fold on time series** → purged+embargoed CV or walk-forward.
- **Same-bar-close execution** → lag one bar, fill next open with spread.
- **Restated fundamentals / current universe** → point-in-time data with delisted names.
- **Magic-mid fills, zero cost** → cross the spread, model impact/funding/borrow, stress 2×.
- **Reporting the best of many trials** → deflated Sharpe / PBO; correct for trials.
- **Judging on mean outcome** → Monte-Carlo the path distribution, read the tail.
- **Sharpe worship** → check skew/kurtosis, autocorrelation, trade count, DSR.
- **One regime / one lucky window** → multi-asset, multi-regime, walk-forward stability.
- **Trusting backtest ≈ live** → paper on live data; monitor tracking error post-deploy.
