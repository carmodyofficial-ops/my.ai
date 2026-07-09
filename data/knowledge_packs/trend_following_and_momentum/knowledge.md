# Trend-Following & Momentum

## Definitions
- **Trend** = a sustained directional drift in *price* over time. **Trend-following** = react to price itself (breakouts, moving averages) — no forecast, just participation.
- **Momentum** = the empirical fact that recent *relative* return predicts future return. A measured *signal* (past N-period return), often used to rank or gate.
- Overlap heavily in practice; "trend-following" usually = time-series momentum implemented with price rules.

## Time-series vs cross-sectional momentum
- **Time-series (TS) momentum** (Moskowitz, Ooi & Pedersen 2012): an asset's **own** past 1-12mo return predicts its next-period return. Up keeps going up. Robust across equities, bonds, FX, commodities, and crypto. Self-de-risking: a falling asset flips you to exit/short = built-in regime filter. This is the core edge.
- **Cross-sectional momentum**: rank a *universe*, long the strongest, short the weakest -> market-neutral basket. Noisier than TS on majors; useful across many alts. Depends on dispersion.

## Entry (matters least — don't curve-fit it)
- **Donchian breakout**: enter when `close > highest_high(N)` (e.g. N=20 or 55), exit on opposite N-low. The classic Turtle system.
- **Moving-average crossover**: long when `fast_MA > slow_MA` (e.g. 20/50 or 50/200).
- **Momentum threshold**: long when `return(lookback) > 0`.
- These are roughly interchangeable. Edge lives in the **exit and sizing**, not the entry trigger.

## Exit IS the strategy
- **Trailing stop, ATR-based** (Chandelier exit): `stop = highest_high_since_entry − k*ATR` (k≈3). Ratchets up, never down. Winners run until the trend genuinely breaks.
- **Cut losers fast** at the same ATR band placed at entry.
- **No fixed take-profit.** A TP caps the right tail — and the right tail is the entire P&L. Capping winners while eating full losers = negative expectancy. Never do it.

## Position sizing by volatility (ATR / vol-targeting)
- `units = (risk_pct * equity) / (k * ATR * point_value)`
- **ATR** (Average True Range) measures per-bar volatility. Sizing off ATR holds **dollar risk per trade constant** across regimes: vol spikes -> ATR rises -> size auto-shrinks.
- Normalizes a 2% BTC day against a 9% one; stops a vol blowup from nuking equity.
- Optionally **vol-target the whole book** to a fixed annualized % (e.g. scale gross so portfolio vol ≈ 15%).

## Regime filter (what makes it not just long beta)
- **Only go long when price > long-term MA (e.g. 200-period). Below it: cash or short.**
- This single rule keeps you OUT of bear markets and sidesteps the 70-80% drawdowns that destroy always-on holders. Without it you're levered buy-and-hold with extra fees.

## Return profile — positive skew & convexity
- Win rate is **~35-45%**. You **lose most trades** — small, capped losses — and a **few massive winners** pay for all of them and then some.
- Distribution is **right-skewed / convex**, like a long-options profile: many small debits, rare large credits.
- **Do not judge by win rate or by stretches of small losses.** Judge by expectancy and the size of the tail. `expectancy = win_rate*avg_win − loss_rate*avg_loss`; here avg_win >> avg_loss carries it.

## Whipsaw in ranges
- Rangebound/chop markets = repeated small stop-outs that bleed equity (the classic trend-following cost).
- Gate with a **regime/vol filter** or **ADX** (only take signals when ADX > 20-25, i.e. a trend actually exists). Fewer, cleaner trades beat trading every cross.

## Diversification across markets
- Trend edge is **thin per market but persistent across many.** The premium comes from breadth: uncorrelated trends fire at different times, smoothing equity.
- Classic CTAs run dozens of markets (FX, rates, commodities, index, crypto). In crypto alone, majors give few independent bets — correlations converge in stress, so crypto-only trend is far more volatile than a cross-asset CTA.

## Drawdown psychology
- Long flat/losing stretches (months) between the big winners are **normal and expected** — the discomfort is the source of the premium. Most abandon the system exactly before the payoff trade.
- The tail winner you need may be 1 in 20 trades; skipping "one bad-looking signal" can skip the trade that makes the year.
- **Pre-commit to the rules.** Discretionary overrides of a systematic trend model usually cut winners early and hold losers.

## Measuring the signal
- **Lookback choice** sets the horizon: short (10-30 bars) = fast, reactive, more whipsaw; long (100-200) = smooth, laggy, fewer trades. Blend multiple lookbacks to avoid single-period luck.
- **Volatility-scaled momentum**: `signal = return(lookback) / realized_vol` — ranks assets on risk-adjusted drift, not raw move; a calm 10% beats a wild 10%.
- **Breakout confirmation**: require a close beyond the band (not an intrabar wick) to avoid stop-run fakeouts.
- **Skip-a-period**: some equity momentum skips the most recent bar (short-term reversal); less common but relevant in crypto's reversion-prone microstructure.

## Why it persists
- **Behavioral**: initial under-reaction to news (anchoring/disposition effect) -> delayed herding/FOMO over-reaction. The drift in between is the trade.
- **Structural**: risk transfer, momentum/flow chasing, slow institutional repositioning.

## Crypto specifics
- Extreme vol -> **wider stops + smaller size** (vol-targeting handles this automatically). Tight stops get wicked out.
- Trends are strong and persistent but punctuated by **violent mean-reverting wicks** — give room.
- 24/7, no close: gaps rare, but funding and liquidations drive overshoots.
- Works best on **BTC/ETH/majors**. Alts whipsaw, thin liquidity, correlated crashes -> momentum decays fast.

## Common mistakes -> Fix
- **Curve-fitting the lookback** (a 47-period high that backtests perfectly = noise) -> Fix: round, robust params; confirm edge is stable across multiple lookbacks/markets.
- **Adding a take-profit** -> caps the tail that funds everything -> Fix: trail the stop, no TP.
- **No trailing stop** -> gives back open profit on every reversal -> Fix: ATR ratchet.
- **Too-tight stops** -> shaken out by normal noise before the trend pays -> Fix: size the stop to ATR, then size the position to the stop.
- **No regime filter** -> long-only-always is just levered beta and eats the full bear -> Fix: 200-MA / trend gate, cash-or-short below.
- **Trading every signal in chop** -> death by whipsaw -> Fix: ADX/vol gate.
- **Judging by win rate** -> abandons a positive-expectancy convex system for looking "wrong often" -> Fix: judge expectancy and tail, not hit rate.
- **Over-concentration in one market** -> crypto-only trend is jumpy and correlation-crashes -> Fix: diversify across markets; size for the crash correlation.
- **Discretionary overrides** -> cut winners early, hold losers -> Fix: pre-commit and follow the system.
