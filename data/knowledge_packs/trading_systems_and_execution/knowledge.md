# Trading Systems and Execution

Educational reference on building/operating trading systems. Not financial advice.

## Pipeline (data → signal → risk → execution → monitoring)
- Market data ingest: normalize, timestamp (exchange vs receipt vs process time), dedupe, gap-detect, handle out-of-order/late ticks. Keep a point-in-time store to avoid look-ahead.
- Signal/alpha: features → prediction → target position/weight. Deterministic given inputs; version the model + feature code.
- Portfolio construction: combine signals, apply constraints (gross/net exposure, per-name caps, sector/factor limits), size positions.
- Pre-trade risk: hard checks BEFORE any order leaves — max order size, notional/position limits, price collar (fat-finger), buying-power/margin, restricted list, self-trade prevention, rate limits.
- Execution: order routing + algos → broker/exchange API → fills.
- Monitoring & reconciliation: real-time P&L, positions, exposure, latency, error rates, alerts.

## OMS vs EMS
- OMS (order management): system of record for orders/positions/allocations, compliance, lifecycle. EMS (execution management): low-latency routing, algos, venue connectivity, real-time book. Boundary blurs in integrated stacks.
- Order state machine: `NEW → PENDING_SUBMIT → SUBMITTED/ACK → (PARTIALLY_FILLED)* → FILLED | CANCELED | REJECTED | EXPIRED`. Every transition is broker-driven and must be logged; never assume a state — confirm via broker callback/poll.

## Smart order routing (SOR)
- Splits/routes a parent order across venues to optimize price, fill probability, fees/rebates, and impact. Considers NBBO, displayed + likely hidden depth, maker–taker economics, and latency to each venue. Anti-gaming: randomize slice size/timing.

## Execution algorithms
- TWAP: even time slices. VWAP: track intraday volume profile. POV/participation: fixed % of realized volume. Implementation shortfall: minimize slippage vs arrival price (Almgren–Chriss impact-vs-timing tradeoff). Choice depends on urgency (signal decay) vs impact tolerance.
- Child-order tactics: post-only/passive to earn spread, peg to mid, cross with IOC when urgent, iceberg to hide size.

## Position sizing
- Fixed fractional: risk a set % of equity per trade; units `= (equity·risk%)/(stop distance)`.
- Volatility targeting: scale position so `position·σ_asset ≈ target σ`; `w_i ∝ target_vol/σ_i`. Rebalance as σ changes.
- Fractional Kelly (¼–½) for growth without ruin-level variance. Always cap by liquidity (≤ x% ADV), gross/net, and per-name limits.

## Fill handling & accounting
- Track parent vs child orders; aggregate partial fills into a weighted-average fill price. Update position, cash, and realized/unrealized P&L per fill event.
- Fees, rebates, borrow/financing, and slippage vs arrival all belong in P&L attribution.
- Handle over-fills, busted trades, and late fills after a cancel request (cancel/replace races).

## Idempotency & reconciliation
- Client order ID (idempotency key) on every submit so retries after timeout/disconnect don't double-send. Never re-submit blindly on an ambiguous ACK — query order status first.
- Reconcile continuously: system position/orders vs broker's authoritative state; alert and halt on drift. Start-of-day and post-disconnect reconciliation are mandatory.
- Exactly-once effect via at-least-one delivery + dedup on server order ID. Persist order intents before sending (write-ahead) so a crash mid-send is recoverable.

## Latency & reliability
- Budget every hop (data→signal→risk→wire→ack). Colocation/kernel-bypass for HFT; for slower strategies, correctness > speed.
- Rate limits: throttle, backoff with jitter, respect venue msg/sec caps; queue and coalesce.
- Idempotent, replayable design; heartbeat/session monitors; auto-reconnect with state resync.

## Kill switches & risk controls
- Global kill switch: cancel all open orders, flatten or freeze, block new orders — one action, tested regularly.
- Automated tripwires: max daily loss (breaker), max drawdown, position/notional breach, error-rate spike, stale-data/heartbeat loss, unexpected fill or position drift, latency blowout.
- Fail-safe defaults: on data loss, disconnect, or ambiguity → stop trading, don't guess. Deploy behind dry-run/paper first; separate research code from production execution.

## Backtest vs live divergence — causes
- Look-ahead bias (future data leaking into features), survivorship bias, in-sample overfitting.
- Fill assumptions too optimistic: filling at mid/close, ignoring spread/impact/queue/non-execution.
- Costs understated: commissions, fees, slippage, borrow, funding.
- Latency/timing: signal acts on data you couldn't have had in time.
- Capacity/impact: strategy size moves the market it backtested on.
- Regime change / non-stationarity; parameter instability.

## Data quality & time
- Timestamp discipline: separate exchange time, receipt time, and processing time; never join features on a future timestamp. Monotonic clocks for latency; NTP/PTP-synced wall clocks for correlation with venue data.
- Detect stale/frozen feeds, sequence gaps, crossed/locked books, and outliers before they reach signal logic; quarantine bad ticks.
- Corporate actions (splits, dividends, symbol changes) must adjust historical + live series consistently.

## Testing & deployment
- Layers: unit tests on signal/risk math → deterministic replay of recorded market data → paper/dry-run against live feed → small-size canary → full size. Promote only on evidence.
- Shadow/parallel run: new system runs alongside prod producing orders that are logged not sent; diff against prod.
- Config as versioned artifact; feature-flag risky changes; keep a one-command rollback and a tested kill switch.

## Order submit skeleton (idempotent)
```
coid = deterministic_id(strategy, ts, symbol, intent)   # idempotency key
persist_intent(coid, order)                              # write-ahead
try: ack = broker.submit(order, client_order_id=coid)
except Timeout: status = broker.query(coid)              # never blind-resend
on_fill(evt): update_position(); reconcile(); attribute_pnl()
```

## Pitfalls → Fix
- Assuming an order state instead of confirming → drive off broker callbacks/polls; treat unknown as unknown, query before acting.
- Re-sending on timeout → idempotency key + status query; write-ahead the intent.
- No reconciliation → continuous position/order recon vs broker; halt on drift.
- Risk checks after the order is sent → all limits are PRE-trade and hard; reject locally.
- No kill switch / untested one → build and drill it; single action to cancel-all + flatten.
- Backtest fills at mid/close → model spread, impact (square-root), queue, and non-fills.
- Shared research/prod code paths → separate, with paper/dry-run gating live.
- Silent failure on data gaps → detect staleness, alert, and stop trading.
- Ignoring partial fills / cancel-replace races → full state machine; handle late fills post-cancel.
- Logging only successes → log every decision, request, response, and rejection to an immutable audit trail.
- Over-sizing to capacity → cap by ADV participation and gross/net/per-name limits; account for impact.
- Clock skew / unsynced timestamps → PTP/NTP sync; monotonic clocks for latency, never join features on future timestamps.
- Untested changes straight to prod → replay + paper + canary before full size; keep one-command rollback and a drilled kill switch.
- Ignoring corporate actions → adjust historical and live series consistently for splits/dividends/symbol changes.
