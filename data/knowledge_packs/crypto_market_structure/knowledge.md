# Crypto Market Structure & Microstructure

## Venues: CEX vs DEX
- **CEX** (Binance, OKX, Bybit, Coinbase, Kraken): central limit order book (CLOB), off-chain matching engine, custodial (they hold your keys/funds), fast (sub-ms match), maker/taker fees. Counterparty = the exchange.
- **DEX** (Uniswap, Curve, dYdX): on-chain settlement, non-custodial (self-custody wallet), pricing via **AMM pool** or on-chain order book. Costs = gas + price impact + MEV. Slower (block time), transparent, permissionless listing.
- **CLOB** = discrete resting bids/asks, price-time priority. **AMM** = continuous curve, always quotes, no counterparty needed to match.

## Instruments: spot vs perps vs dated
- **Spot** = direct ownership of the asset, settled now.
- **Perpetual futures (perps)** = leveraged derivative, **no expiry**, dominant crypto venue (often >70% of volume); deepest liquidity and primary price discovery. Tethered to spot by **funding**.
- **Dated futures** = fixed expiry, carry **calendar basis** (contango = future>spot, backwardation = future<spot) -> annualized basis trade.
- **Options** (mostly Deribit): thinner; dealer gamma / max-pain pins matter near expiry. Trade where liquidity is — usually perps.

## Funding rates (perp anchor)
- Perps have no expiry, so **funding** payments tether mark price to spot index.
- `funding > 0` -> **longs pay shorts** (perp > spot, longs crowded). `funding < 0` -> shorts pay longs.
- Paid ~every 8h (00:00/08:00/16:00 UTC), charged on **notional** -> leverage amplifies the bleed. `payment = position_notional * funding_rate`.
- Read three ways: (1) **cost** of holding leveraged exposure; (2) **positioning signal** — extreme positive = crowded longs, long-squeeze risk; (3) **carry** — long spot / short perp = delta-neutral, harvest positive funding. Persistent extremes precede flushes.

## Basis
- **Basis = futures price − spot price.** Annualized basis on dated futures = implied yield of cash-and-carry.
- **Contango** (positive basis) is normal in bull demand; **backwardation** (negative) signals stress/short demand.
- Basis and funding converge at settlement/via arbitrage; divergence = a tradable spread with counterparty/liquidation risk.

## Leverage & liquidations + cascades
- **Isolated margin** = loss capped to one position's margin. **Cross margin** = whole wallet backs positions (one bad trade can liquidate everything).
- **Liquidation** = forced close when margin < maintenance. **Cascade**: long liqs -> forced market sells -> price drops -> more longs underwater -> more liqs (feedback loop). Shorts cascade upward symmetrically.
- Produces violent **wicks** that hunt resting stops then snap back. **Liquidation clusters act as magnets** — price gravitates to pools of liq levels; heatmap zones are targets, not support. Aggregated liq prints mark capitulation extremes.

## AMMs (constant-product)
- **Constant product**: `x * y = k`, reserves of two tokens, invariant `k`. Price = `y/x` (ratio of reserves).
- A trade of `dx` moves reserves along the curve: `dy = y − k/(x+dx)`. **Larger trades = worse price** (slippage scales superlinearly) because you slide up the hyperbola.
- **Slippage** = executed price vs quoted mid; set a `min_amount_out` / slippage tolerance to bound it.
- **Impermanent loss (IL)** = LP value vs just holding, when the price ratio diverges. IL grows with divergence; a 2x price move ≈ 5.7% IL, 4x ≈ 20%. "Impermanent" only if price returns; realized on withdrawal. Fees earned must exceed IL for LPing to profit.
- Variants: Curve StableSwap (flat near peg for correlated assets), Uniswap V3 **concentrated liquidity** (LP picks a price range -> higher capital efficiency, but IL and range-exit risk amplified).

## Order-book vs pool liquidity
- **Order book**: resting size per level (**depth**), spread = best_ask − best_bid. Thin alt books -> modest size walks multiple levels.
- **Pool**: liquidity is the curve's `k` / reserves; deeper pool = flatter price impact. No spread, but every trade pays the curve + gas + MEV.

## Stablecoins
- **Fiat-backed** (USDT, USDC): issuer holds reserves (cash/T-bills). Peg risk = issuer solvency, reserve quality, redemption gating.
- **Crypto-collateralized** (DAI): over-collateralized by on-chain assets; peg via liquidations/incentives.
- **Algorithmic** (UST): no/under collateral, peg by mint-burn arbitrage — **reflexive and fragile** (UST -> ~0 in the Terra collapse).
- Stables are the quote and collateral leg -> "USD" exposure is really **issuer/peg credit risk**. **Depeg** (USDC dipped ~0.88 during SVB) breaks pricing, triggers cascades, and is itself tradable. Treat stables as a risk factor, not cash.

## On-chain vs off-chain
- **Off-chain** (CEX): trades in the matching engine, only deposits/withdrawals touch the chain. Fast, private, custodial.
- **On-chain** (DEX): every trade is a signed transaction, publicly visible in the mempool before confirmation -> exposed to MEV, block latency, reorg/finality risk, gas spikes.

## Market hours: 24/7
- No open/close, no overnight gaps, no circuit breakers. Price discovery never pauses -> risk can't be "parked" over a weekend.
- Liquidity ebbs on weekends/holidays and in the Asia->US handoff: thinner books, wider spreads, larger slippage, sharper wicks. Funding settlements impose an 8h rhythm on flows.

## Fees
- **Maker** = resting limit order, adds liquidity, earns rebate / pays lower fee. **Taker** = market/marketable order, removes liquidity, pays higher fee + crosses spread.
- **Gas** = on-chain execution cost (DEX), independent of trade size, spikes with network congestion.
- Fee tiers scale with 30d volume. High-frequency edge lives or dies on fees.

## MEV (Maximal Extractable Value)
- Value extracted by reordering/inserting/censoring transactions in a block. Affects on-chain (DEX) flow.
- **Front-running**: bot sees your pending swap, buys ahead. **Sandwich**: buy before + sell after your trade, you get the worst fill. **Back-running/arb**: rebalances pools post-trade.
- Mitigate: tight slippage limits, **private order flow** (Flashbots Protect / private mempools), commit-reveal, MEV-aware routers.

## Pitfalls -> Fix
- **Trading illiquid alt books** -> size walks levels, huge slippage. Fix: size into depth; maker/TWAP/iceberg for size, taker only when urgency > cost.
- **Ignoring funding on leveraged holds** -> silent bleed compounds every 8h. Fix: price funding into carry/hold cost; watch extremes as squeeze signals.
- **Treating liq heatmap zones as support** -> price hunts them. Fix: expect wicks toward liq clusters; place stops away from obvious pools.
- **Assuming stablecoins = cash** -> depeg breaks the quote leg. Fix: treat peg as credit risk; diversify collateral, watch reserve/redemption news.
- **DEX swap with loose slippage** -> sandwiched by MEV. Fix: tight slippage tolerance + private RPC.
- **Backtesting on current listings only** -> survivorship bias; dead/delisted coins vanish, overstating returns. Fix: point-in-time universe.
- **Trusting low-tier CEX volume** -> wash trading inflates metrics. Fix: weight proven venues; verify volume vs on-chain/orderbook depth.
- **Cross-margin on a volatile alt** -> one liq wipes the wallet. Fix: isolated margin, hard position caps.
- **Assuming your venue can't fail** -> hacks, halts (often mid-crash), withdrawal freezes, oracle/funding glitches are real. Fix: split custody across venues; counterparty risk is a live position.
