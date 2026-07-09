# Categories of Edge in Crypto Trading

## The hard truth first
- Most TA/indicator strategies (RSI, Bollinger, MA-cross, breakout) are **long-biased beta in disguise** — they ride bull markets, get destroyed in bears. After fees + slippage, edge collapses toward zero.
- If your equity curve tracks BTC, you have **no alpha** — you have exposure you could get free by holding spot.
- The one question for any strategy: *what does it do in a −40% quarter?* If the answer is "stays long," it is not an edge.
- **Edge = one of three must be true:** (a) **market-neutrality** (arb/pairs/funding), (b) a **regime filter** (cash or short in downtrends), or (c) the **ability to short.** Long-only-always = beta, full stop.

## Categories of edge (and why each works)
1. **Momentum (time-series & cross-sectional)** — the only TA family with robust academic support. Trends persist 1-12mo (under-reaction, flows, herding). TS-momentum self-de-risks: a falling asset signals exit/short = built-in regime filter. Cross-sectional: long strongest / short weakest of a universe -> market-neutral. Decays as crowded and as vol regime shifts.
2. **Mean-reversion** — fade over-extension back to a statistical center (z-score, Bollinger, RSI). Works in **range/chop**, blows up in trends (you fade a move that keeps going). Needs a trend filter to switch off. Short half-life, fee-sensitive.
3. **Carry / funding** — long spot + short perp = delta-neutral, collect positive funding. Edge = structural retail leverage demand paying to be long (often +5-30% APR in bull froth). Risks below.
4. **Basis / arbitrage** — cash-and-carry on dated futures (lock annualized basis), cross-exchange price gaps, triangular arb, DEX-CEX gaps. Edge is structural but competitive and thin.
5. **On-chain signals** — exchange in/outflows, stablecoin mints (dry powder), whale/entity flows, liquidations, unlocks/vesting, miner behavior. Real but data-intensive; noisy; front-run by sophisticated flow.
6. **Market-making / liquidity provision** — quote both sides, capture spread + rebates. Edge is real but **operational**: low latency, adverse-selection control, tight inventory risk. You lose when informed flow runs you over.

## Funding-rate carry mechanics
- Position: **long spot, short equal-notional perp** -> price-neutral (delta ≈ 0). P&L = funding received on the short perp.
- `carry_return ≈ Σ funding_payments − fees − borrow`. Funding paid ~every 8h on notional.
- Positive when perps trade at a premium (crowded longs). APR = `funding_per_8h * 3 * 365`.
- **Failure modes:** funding flips negative (you now pay), spot-perp basis gaps against you before convergence, the short leg gets **liquidated** in a squeeze (needs margin buffer), exchange counterparty/withdrawal risk, stablecoin depeg on the collateral leg.

## Cross-exchange arb — why it's hard
- The gap you see is usually **not capturable**: fees (both legs) + withdrawal fees + slippage often exceed it.
- **Latency race** — HFT closes gaps in milliseconds; retail sees stale prices.
- **Transfer latency** — moving coins between venues takes minutes-to-blocks; the gap is gone on arrival. Requires **pre-funded inventory on both sides** = capital lockup + venue risk.
- **Withdrawal halts** exactly during the volatility that creates the gap.
- Real arbs are **inventory-balanced** (rebalance passively), low-margin, high-turnover, infrastructure-heavy.

## Liquidation "hunting" (concept)
- Leverage concentrates stops/liq levels at visible price zones (round numbers, prior highs). Price tends to **gravitate to liquidation clusters** — hitting them triggers forced fills that fuel the move (cascade), then often snaps back.
- As a *signal*: extreme leverage + a liq heatmap wall = elevated squeeze probability. It is not "manipulation you can front-run" reliably; treat it as an over-extension/positioning read, not a guarantee.

## Why edges decay
- **Crowding** — publicized edge attracts capital, spread/premium compresses to zero.
- **Regime change** — a bull-market pattern dies in a bear; correlations converge to 1 in stress.
- **Adaptation** — market participants and bots learn the pattern and fade it.
- **Cost creep** — as you scale, slippage and impact eat the thin margin.

## Backtesting crypto data caveats
- **Survivorship bias** — dead/delisted coins vanish; backtests over current listings overstate returns. Use point-in-time universes.
- **Wash trading** — fake volume inflates low-tier CEX/token metrics; liquidity you "assumed" isn't there. Weight proven venues.
- **Bad data** — gaps, bad ticks, exchange-specific candles, timestamp/timezone drift, forks/ticker-reuse discontinuities.
- **Short history** — a sample that never saw 2018 or 2022 hasn't seen tail risk. Deeper history exposes it.
- **Look-ahead** — using a candle's close (or future data) to trade that candle. Fees/slippage unmodeled inflate everything.

## Risk (structural, not just price)
- **Exchange counterparty** — insolvency (FTX), hacks, halts, withdrawal freezes; assume your venue can fail. Split custody.
- **Depegs** — stablecoin collateral leg can break; a carry/arb trade can be sunk by peg risk, not price.
- **Liquidation of the hedge leg** — delta-neutral only if both legs survive; margin the short.
- **Correlation crash** — "uncorrelated" alt baskets converge to 1 in stress; size for the crash correlation.

## Edge-validation discipline
- Validate **out-of-sample AND walk-forward across MULTIPLE regimes** (bull, bear, chop). One OOS split can itself be lucky — re-fit rolling windows.
- **In-sample Sharpe > 3 = overfit,** not genius. Be suspicious of beauty.
- Require **enough trades** — under-trading games Sharpe and hides nothing-strategies behind a few lucky bets.
- **Model fees + slippage always.** They kill most paper edges.
- Default prior: your backtest is wrong and your edge is smaller than it looks. Prove otherwise.
- Sizing is alpha: **vol-targeted sizing**, **regime filters**, **fractional Kelly** (1/4-1/2, never full), **hard max-drawdown kill-switch.** Survival compounds; ruin is absorbing.

## Pitfalls -> Fix
- **Overfitting to the bull market** -> strategy is levered buy-and-hold. Fix: test the last full bear; demand a short/cash branch.
- **Judging by in-sample Sharpe** -> beauty = overfit. Fix: walk-forward, multi-regime, min-trade count.
- **Ignoring fees/slippage** -> paper edge evaporates live. Fix: model real costs; if edge < 2x costs, it's noise.
- **Assuming the arb gap is free** -> latency + transfer + fees eat it. Fix: pre-funded inventory, cost-net the gap first.
- **Un-margined hedge leg** -> "delta-neutral" gets liquidated in a squeeze. Fix: buffer margin, isolated risk.
- **Trusting exchange volume** -> wash trading fakes liquidity. Fix: cross-check depth and on-chain flow.
- **Full Kelly / all-in on one venue** -> one shock = ruin. Fix: fractional Kelly, diversified custody, kill-switch.
