# Finance & Trading
Educational/analytical reference only — not personalized investment advice, not a recommendation to buy/sell. Sizing/risk numbers are illustrative; the operator owns every live decision.
## Risk & position sizing
- Risk per trade in **R** units: `R = entry - stop` (per share/contract). Size so $-risk = account × risk%. Shares = (account × risk%) / R. Typical risk% = 0.25–1.0% per trade.
- **Fixed-fractional**: risk constant % of *current* equity → geometric compounding, auto-deleverages in drawdown.
- **Kelly**: `f* = edge/odds = (p·b − (1−p))/b`; for continuous returns `f* ≈ μ/σ²`. Full Kelly is too volatile in practice — trade **fractional Kelly (¼–½)**; Kelly assumes known edge, real edge is estimated → overbet risk.
- Stop discipline: define stop *before* entry, from structure/ATR not P&L tolerance. Never widen a stop to avoid a loss. Move to breakeven only on structural confirmation, not hope.
- Portfolio heat = sum of open risk. Cap total heat (e.g. ≤ 3–6R) and correlated-cluster risk (correlated names ≈ one bet).
## Strategy evaluation
- **Sharpe** = (Rp − Rf)/σp, annualize ×√periods (√252 daily). **Sortino** uses downside deviation only. **Calmar** = CAGR / |maxDD|.
- **Max drawdown (maxDD)**: largest peak-to-trough; recovery from −50% needs +100%. Track drawdown *duration* too.
- **Profit factor** = gross profit / gross loss (>1.5 decent). **Expectancy** = avg win×winrate − avg loss×lossrate, express in R.
- Low win-rate + high payoff and high win-rate + low payoff can share the same expectancy — judge by expectancy and tail, not win-rate alone.
## Backtesting hygiene
- **Look-ahead/leakage**: only use data available at decision time; lag signals; beware same-bar fills at unattainable prices; point-in-time fundamentals, not restated.
- **Survivorship bias**: include delisted/dead names or results inflate.
- **Overfitting**: too many params / too few trades. Guard with walk-forward, out-of-sample holdout, parameter-plateau (not spike) sensitivity, and deflated Sharpe for multiple-testing.
- Model realistic **costs**: commission, spread, slippage, borrow/financing, market impact. Frictionless backtests lie.
- Sim ≠ live: partial fills, queue position, rejects, latency, gaps through stops.
## Market structure basics
- Order types: market (pays spread, certainty), limit (price certain, fill uncertain), stop/stop-limit (stop-market can slip badly on gaps), IOC/FOK, marketable-limit for control with urgency.
- Liquidity: bid/ask spread, depth, ADV. Sizing vs ADV drives impact. Wide spread ⇒ marketable orders bleed edge. Participation rule of thumb: keep order ≤ 1–5% of ADV to limit impact.
- Session effects: open/close volatility, overnight gap risk, thin premarket/after-hours, auction imbalances, weekend/holiday gaps (esp. 24/7 crypto vs gated equity hours where the gap prices in over the weekend and hits at Sunday/Monday open).
- Slippage sources: spread, latency, impact, adverse selection (your fill is worst when informed flow is against you). Track realized vs expected fill (implementation shortfall).
## Trade management & psychology
- Plan the whole trade before entry: entry trigger, stop, target(s), size, and invalidation. Pre-commit; don't renegotiate mid-trade.
- Scale-outs bank partial R and lower stress but cap upside — asymmetric strategies favor letting winners run past 2–3R with a trailing stop.
- Losing streaks are expected: with a 40% win rate, a 6-loss streak has ~5% probability *per window* — it will happen. Size so a normal streak (or a max-DD run) doesn't cross a psychological or ruin threshold.
- **Risk of ruin** rises fast with per-trade risk and negative expectancy; positive edge + small fractional sizing keeps ruin negligible.
## Portfolio construction
- Diversify across *uncorrelated return streams*, not just tickers. Effective bets ≈ n / (1 + (n−1)ρ) — high ρ collapses many positions into one.
- Volatility parity: weight inversely to σ so each position contributes similar risk. Rebalance discipline > forecasting.
- Regime awareness: correlations trend toward 1 in crises (diversification fails exactly when needed) — hold genuine tail hedges or cash, not just "different" longs.
## Strategy edge & style
- Two return sources: **mean-reversion** (fade extremes; works in ranges, dies in trends) and **momentum/trend** (ride persistence; works in trends, chops in ranges). Know which regime pays your strategy and size down in the wrong one.
- Edge = positive expectancy after costs. Sources: informational, structural (liquidity provision, rebalance flows), behavioral, risk-premium harvesting. Decaying edge is normal — monitor live vs backtest divergence and retire fading strategies.
- Signal-to-noise in returns is low; more data/features ≠ more edge — usually more overfit. Prefer few robust drivers with economic rationale.
## Analysis vs advice boundary
- This material informs *analysis and process*: framing risk, evaluating a strategy's statistics, spotting methodological errors. It is **not** a buy/sell/hold recommendation, price target, or personalized allocation.
- Position sizes, thresholds, and examples here are illustrative defaults — not prescriptions for any account. Actual live decisions depend on the operator's mandate, capital, constraints, and risk tolerance, and remain the operator's responsibility.
## Gotchas -> Fix
- **Great backtest, dead live**: overfit or leaked. Re-run out-of-sample, add costs, check same-bar fills, degrade params — real edge survives perturbation.
- **Sharpe looks amazing (>3 daily strat)**: likely leakage, stale prices, or ignored costs. Audit the fill logic.
- **Averaging down a loser**: raises risk as thesis weakens; not a strategy — it's the absence of a stop.
- **Position too big "high-conviction"**: single-name blowup dominates. Cap per-name and per-cluster heat.
- **Optimizing on full history**: in-sample mirage. Only walk-forward / OOS results count.
- **Comparing raw returns**: ignore risk. Compare Sharpe/Sortino/Calmar and drawdown path.
- **Vol targeting w/o regime check**: σ estimate lags; vol spikes deleverage after the damage. Use faster estimators / floors.
- **Ignoring correlation**: 5 tech longs = 1 big tech bet. Net exposure, not gross count, is the risk.
