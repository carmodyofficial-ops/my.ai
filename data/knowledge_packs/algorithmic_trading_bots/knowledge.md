# Algorithmic Trading Bot Reference

Educational engineering reference — how to build/operate a bot safely, not financial advice.

## Architecture (layers)
`data feed → strategy/signal → risk layer → execution → state/persistence → monitoring`
- **Separate signal from execution.** Strategy emits *target positions*; an execution layer reconciles current→target. Never place orders inside signal code.
- **Risk layer sits between signal and execution** and can veto/clamp: per-trade risk, max exposure, correlation cap, kill-switch flags. Enforce limits **in code, not discipline**.
- **State/persistence:** positions, pending orders, equity, order-id map, kill-switch — to disk/DB, written **before** acting. Crash → reload truth from the broker, not from memory.
- **Monitoring:** heartbeat, PnL, error rate, disconnects, order-reject rate → alerting + a manual kill switch.

## Event loop vs polling
- **Event-driven (websocket/callbacks):** react to ticks/fills/book updates. Low latency, but must handle reconnect gaps, out-of-order events, and backpressure.
- **Polling (REST on interval):** simpler, deterministic cadence; higher latency, burns rate limit, can miss between polls.
- Hybrid is common: **websocket for market data + REST as source-of-truth for account/orders** (poll to reconcile). Never fully trust a stream for balances.

## Order lifecycle & reconciliation
- States: `new → submitted (accepted) → partially_filled → filled | canceled | rejected | expired`. Track each order through them.
- **Reconciliation loop** (periodic + on reconnect): pull open orders, positions, balances from the broker; diff against local state; repair drift. Broker is **source of truth**.
- On restart: **do not assume** local state — fetch open/filled orders first, rebuild, then act.

## Idempotency & double-order prevention
- Attach a **`client_order_id`** (deterministic key) to every order. On reconnect/timeout, query by that id before resubmitting — **never blind-resubmit**.
- A submit that **times out is unknown, not failed**: reconcile before retrying, or you double-fill.
- Make the whole submit path idempotent: same intent + same id → at most one live order.

## Rate limits
- Respect per-endpoint weights; **token-bucket** limiter client-side. Back off on `429`; read `Retry-After`.
- Batch/cancel-replace instead of spamming; prioritize critical calls (cancel > new order > market data) when throttled.

## Error handling & retries
- **Exponential backoff + jitter** on transient errors (network, 5xx, 429). Cap attempts.
- **Classify errors:** transient (retry) vs terminal (insufficient funds, invalid params → don't retry, alert). Retrying a rejected-for-cause order loops forever.
- **Retries must be idempotent** (see client_order_id) or they duplicate orders.
- Treat missing/stale data as **no-signal**, not stale-signal. Staleness check: if last tick age > threshold → halt trading, don't act on old prices.

## Kill switches & circuit breakers
- **Manual kill switch:** one flag that flattens/halts; reachable out-of-band (not only via the crashing process).
- **Automatic circuit breakers:** max daily loss, max drawdown (e.g. halt at −X%), per-minute order count, reject-rate spike, feed-staleness, position-limit breach, price sanity (fat-finger) check.
- Breaker action: **stop new orders, optionally flatten, alert, require human reset.** Fail *closed* (halt on uncertainty).

## Config vs code
- Parameters (symbols, sizes, thresholds, limits) in **versioned config**, not hardcoded. Separate **secrets** (keys) from config; never commit keys.
- Distinct **environments** (paper vs live) selected by config, with loud visual/log distinction. Validate config on startup; refuse to run on bad/missing values.

## Logging & alerting
- **Structured logs** (JSON) with timestamps, order ids, correlation ids. Log every order intent, submission, ack, fill, cancel, reject — an **immutable audit trail**.
- Alert on: disconnects, reject spikes, PnL breaches, breaker trips, reconciliation mismatches, staleness. Route critical alerts to a channel a human actually watches.

## Dry-run / paper mode
- Deployment ladder: **backtest → paper/dry-run (live data, simulated fills) → small live → scale.** Never skip paper.
- Paper mode should exercise the **same code path** (feed, risk, execution, state) with a simulated broker — differences hide bugs.
- Paper won't reproduce real latency, partial fills, queue position, or market impact — treat small-live as the real test.

## Execution details
- **Order types:** market = fill certainty + slippage; limit = price control + non-fill risk; stop/stop-limit for exits; IOC/FOK for immediacy; post-only to guarantee **maker** (rebate) vs **taker** (crosses spread, pays).
- **Time-in-force** (GTC/DAY/IOC): pick deliberately — a stale GTC left after a crash can fire against a moved market.
- **Slicing large orders** (TWAP/VWAP/iceberg) to limit market impact; respect order-book depth and don't chase your own footprint.
- **Clock discipline:** sync to NTP; use exchange/server time for bar boundaries and expiries, not local wall clock.

## Common failure modes → Fix
- **Double orders** (timeout then retry) → `client_order_id` + query-before-resubmit; idempotent submit path.
- **Stale/frozen data acted on as live** → tick-age staleness gate; halt on gap; websocket for data + REST reconcile for truth.
- **Partial fills mishandled** → track filled vs requested; size next action on *actual* position; cancel/replace the remainder deliberately.
- **State drift after crash/reconnect** → reconcile from broker on startup and periodically; persist state before acting.
- **Silent disconnect** → heartbeat + reconnect with backoff; treat missing data as no-signal; alert.
- **Rate-limit ban mid-session** → client-side limiter, honor `Retry-After`, prioritize cancels.
- **Retry storm on terminal errors** → classify errors; don't retry rejects-for-cause; cap attempts; alert.
- **No kill switch / limits only "in discipline"** → hard circuit breakers in code, daily-loss + drawdown halts, out-of-band manual kill.
- **Fat-finger / bad price order** → price/qty sanity checks vs last trade and limits before submit.
- **Secrets in code / wrong environment** → env-selected config, secrets in a vault, loud paper-vs-live guard.
- **Fees/slippage ignored** → model taker cost + slippage; #1 paper-to-live killer.
- **Discretionary override** → the coded rules are the edge; manual meddling breaks the tested system.
