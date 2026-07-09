# Market Microstructure

Educational reference on how markets actually trade. Not financial advice.

## Limit order book (LOB)
- Continuous double auction: resting limit orders (passive liquidity) matched against incoming market/marketable orders (aggressive demand).
- Best bid (highest buy) / best ask (lowest sell); NBBO = national best bid/offer across venues.
- Spread: `ask - bid`; relative spread `= spread / mid`. Mid `= (bid+ask)/2`. Microprice (size-weighted mid) `= (bid·ask_size + ask·bid_size)/(bid_size+ask_size)` — leans toward the side with less size, a short-horizon fair-value predictor.
- Depth: resting size at each price level; the shape of cumulative depth = the market's price-impact function.
- Price–time priority (most venues): better price fills first, then earliest at that price (FIFO). Some venues use pro-rata (size-weighted).
- Tick size: min price increment; constrains spread and shapes queue dynamics (small tick → thin queues, frequent price updates).

## Order types
- Market: immediate fill, takes liquidity, pays spread + impact; no price guarantee.
- Limit: price cap; posts liquidity if non-marketable, joins the queue; risks non-execution.
- IOC (immediate-or-cancel): fill what's available now, cancel the rest. FOK (fill-or-kill): all-or-nothing immediately. Post-only / ALO: rejects/reprices if it would take (guarantees maker rebate, avoids taker fee). Iceberg/reserve: shows small display size, hides the rest. Pegged: floats with bid/ask/mid. Stop / stop-limit: dormant until trigger, then becomes market/limit.

## Maker vs taker; fees
- Maker posts resting liquidity (often earns a rebate); taker crosses the spread (pays a fee). Maker–taker fee schedule shapes routing.
- Effective spread `= 2·|price - mid|` (execution cost vs mid at arrival). Realized spread `= 2·|price - mid_{t+Δ}|` (maker's captured spread after adverse move). Effective − realized ≈ adverse selection / price-impact component.

## Price formation & liquidity
- Price = equilibrium where marginal buy/sell orders meet; informed order flow moves it, uninformed (noise) flow provides the spread's revenue.
- Liquidity dimensions: tightness (spread), depth (size), resiliency (how fast the book refills after a hit), immediacy.
- Order flow imbalance (OFI) and trade sign (Lee–Ready / tick rule) predict short-horizon returns.
- Kyle's lambda: price impact per unit signed volume, `ΔP = λ·Q`; λ ∝ informed-trading intensity / inverse depth.

## Slippage & market impact
- Slippage: realized price − decision/arrival price (includes spread, impact, timing, fees).
- Temporary impact: transient, book refills (liquidity cost). Permanent impact: information leakage that shifts fair value.
- Square-root law (empirical): impact `≈ Y·σ·√(Q/ADV)` — cost scales with volatility and the SQRT of participation (order size / average daily volume), not linearly. Doubling size raises cost ~1.4×, not 2×. Implication: split large orders over time.
- Almgren–Chriss: optimal execution trades off market impact (trade fast) vs timing/volatility risk (trade slow); yields a scheduled trajectory given risk aversion.

## Adverse selection
- Resting limit orders get filled preferentially when the market is about to move against them (you buy right before it drops). Makers earn the spread but pay adverse selection; net edge = spread − adverse selection − fees + rebates.
- Glosten–Milgrom: spread exists to compensate market makers for trading against possibly-informed counterparties.

## Latency & queue position
- Queue position (FIFO): earlier in queue → higher fill probability, less adverse selection. Cancelling and re-posting loses your spot.
- Latency matters for: getting to the front of the queue, cancelling stale quotes before being picked off, and racing to take mispriced liquidity. Colocation / low-latency infra is a microstructure edge.
- Quote fading: displayed liquidity vanishes as you reach for it (latency + cancels).

## Dark pools & hidden liquidity
- Dark pools: no pre-trade transparency; execute (often at midpoint) to reduce impact for large blocks; risk of information leakage and adverse selection from toxic flow.
- Hidden/iceberg orders add undisplayed depth; the visible book understates true liquidity.

## Execution algos
- TWAP: time-weighted, even slices over an interval — schedule-driven, ignores volume.
- VWAP: volume-weighted, slices tracking the historical intraday volume profile (U-shaped: heavy at open/close); benchmark = session VWAP.
- POV / participation: trade a fixed % of realized volume (adaptive to actual activity).
- Implementation shortfall (IS): minimize slippage vs arrival (decision) price; front-loads to cut timing risk (Almgren–Chriss style). Best when signal is time-sensitive.

## Crypto/perps specifics
- Perpetual funding rate: periodic payment tying perp to spot; longs pay shorts when perp > spot (positive funding) and vice versa; drives carry and mean reversion of basis.
- Basis: futures − spot; contango (future > spot) vs backwardation. Liquidation cascades: forced deleveraging → gap moves, spread blowout, thin books.

## Auctions & special sessions
- Opening/closing auctions: batch all orders and cross at a single price maximizing executable volume; large size prints with less continuous-market impact. Closing auction is the deepest liquidity of the day for equities (index rebalances, MOC/LOC orders).
- Halts / circuit breakers: volatility interruptions pause continuous trading, then reopen via auction; spreads gap around them.

## Flow toxicity
- Toxic flow = order flow that is informed / adversely selects makers. VPIN (volume-synchronized prob of informed trading) estimates toxicity; rising toxicity precedes spread widening and maker withdrawal.
- When toxicity spikes, makers pull quotes → depth collapses → impact and slippage jump (feedback into liquidation cascades and flash crashes).

## Worked impact example
- Order = 5% of ADV, daily σ = 2%, `Y ≈ 0.5`: impact `≈ 0.5·0.02·√0.05 ≈ 0.22%`. Doubling to 10% ADV → `0.5·0.02·√0.10 ≈ 0.32%` (~1.4×, not 2×) — the SQRT scaling that motivates slicing.

## Pitfalls → Fix
- Backtesting fills at mid or close → assume you pay the spread + queue; model marketable orders at ask/bid, passive fills only if price trades through your level.
- Ignoring market impact → apply square-root cost `Y·σ·√(Q/ADV)`; cap participation (e.g. ≤5–10% ADV).
- Assuming displayed depth is real → account for hidden/iceberg and quote fading; stress-test against thin books.
- Signal alpha ≠ executable alpha → subtract spread, impact, fees, latency; an edge smaller than costs is negative net.
- Posting passive and assuming instant fill → model queue position and non-execution; passive fills are adverse-selected.
- Sweeping the book with a market order → walks up multiple levels; use limits/IOC and slice.
- Ignoring maker/taker economics → post-only for rebates when non-urgent; taker only when immediacy is worth the fee + impact.
- Using session VWAP as a live target → it's only known ex-post; track a forecast volume profile.
- Trading illiquid names / open/close auctions naively → wider spreads, gaps; prefer liquid windows or participate in the auction.
- Same order twice on latency retries → idempotency keys / client order IDs (see execution systems).
