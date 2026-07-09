# Event-Driven Architecture

## Events vs commands vs messages
- **Event**: a statement of fact, something that **happened** — past tense, immutable (`OrderPlaced`, `PaymentCaptured`). Publisher doesn't know/care who consumes; 0..N consumers.
- **Command**: a request to **do** something — imperative (`PlaceOrder`), directed at one handler, can be rejected/fail. Expresses intent, not fact.
- **Message**: the transport envelope carrying either. Has headers (id, type, timestamp, correlation/causation id, schema version) + payload.
- Producers emit events without knowing consumers → **loose coupling, inversion of dependency**. New consumers plug in with zero producer changes.

## Notification vs event-carried state transfer
- **Event notification**: thin event ("`OrderPlaced{orderId}`"); consumer calls back to fetch details. Small payloads, but adds coupling + query load back on the producer, and risks read-your-own-race.
- **Event-carried state transfer (ECST)**: event carries all needed data; consumers keep a local copy, no callback. Decoupled + resilient (works if producer is down), but fatter events + data duplication + staleness.
- Choose ECST when consumers need autonomy/availability; notification when payloads are huge or consumers rarely need the full data.

## Event sourcing
- Persist state as an **append-only log of events**; current state = **fold/replay** of all events. The event log is the source of truth, not a snapshot table.
- Benefits: complete audit trail, temporal queries ("state as of T"), rebuild any projection, debug by replay.
- **Snapshots**: periodically persist folded state so replay starts from the last snapshot instead of event #1 — bounds rebuild cost for long-lived aggregates.
- **Projections/read models**: subscribe to the event stream and build query-optimized views; rebuildable from the log at any time.
- Costs: steep learning curve, event **schema versioning is mandatory and forever** (you replay old events for the life of the system), no easy `DELETE`/`UPDATE` (append a corrective event).
- Not the same as CQRS and not required for EDA — use only when audit/temporal/replay needs justify it.

## CQRS
- **Command Query Responsibility Segregation**: separate the **write model** (validates commands, enforces invariants, normalized) from the **read model** (denormalized, query-shaped, often many per use case).
- Read models updated asynchronously from write-side events → **eventually consistent** (read may lag the write).
- Pairs naturally with event sourcing (project events into read models) but is independent — you can do CQRS on plain CRUD.
- Use when read and write loads/shapes diverge sharply; adds complexity, so don't apply blanket to simple CRUD.

## Eventual consistency
- In EDA, cross-service/cross-view state converges **after** a delay, not instantly. Design UX and invariants for it (show "processing", read-your-writes via client-side echo or sticky read).
- Never assume a downstream projection reflects a write immediately after publishing.
- Keep true invariants **inside one aggregate/local transaction**; everything across boundaries is eventual and reconciled via events/compensation.

## Idempotency & dedup
- Delivery is **at-least-once** in practice → consumers must be **idempotent** (processing the same event twice = same result).
- Techniques: dedupe by **event id** (store processed ids / unique constraint), upsert instead of insert, conditional writes (compare version), natural idempotency (setting a value vs incrementing).
- Track a **processed-events table** or use the message id as an idempotency key; drop duplicates.

## Ordering & partitioning
- Global ordering across a topic is generally impossible/expensive. Order is guaranteed only **within a partition** (Kafka) / message group (SQS FIFO).
- Partition by a **key that must stay ordered together** (e.g. `aggregateId`/`customerId`) so all events for one entity land in one partition and stay in order.
- Trade-off: hot keys create partition skew; too-coarse keys kill parallelism. Consumers must tolerate cross-partition reordering.
- Use **causation/version numbers** in events so consumers can detect/handle out-of-order arrival (ignore stale, buffer gaps).

## Outbox pattern (dual-write problem)
- **Dual-write problem**: writing to the DB *and* publishing to the broker as two separate operations is **not atomic** — a crash between them loses the event or emits a phantom.
- **Transactional outbox**: in the **same local DB transaction** as the state change, insert the event into an `outbox` table. A separate relay (polling or **CDC** via Debezium reading the WAL/binlog) publishes outbox rows to the broker, then marks them sent.
- Guarantees at-least-once publish consistent with the DB commit. Consumers dedupe (relay may re-publish on crash).
- **Inbox pattern**: mirror on the consumer side — record processed message ids to dedupe.

## Topologies & delivery
- **Broker topology** (message spine — Kafka/Rabbit/Pulsar): events flow through a central log/broker; consumers subscribe independently. Highly decoupled, scalable, replayable. Harder to reason about end-to-end flow.
- **Mediator topology** (orchestrator coordinates a workflow): a component owns the process, dispatches steps as events/commands, tracks completion. Explicit, observable; the mediator is a coupling point.
- **Consumer groups / partitions**: scale consumers horizontally; the broker splits partitions across group members so each partition is processed by one consumer (ordered, parallel across partitions).
- **Fan-out**: one event → many independent consumers (analytics, search index, notifications, audit) with zero producer changes — the core EDA payoff.
- **Backpressure**: pull-based consumers (Kafka poll) self-throttle; push-based need flow control/prefetch limits so a slow consumer doesn't get overrun.

## Schema / event versioning
- Events are a **long-lived contract**, read by future consumers and (in event sourcing) replayed forever. Evolve carefully.
- **Backward-compatible changes only**: add optional fields with defaults; never remove/rename/retype/repurpose a field.
- Use a schema registry (Avro/Protobuf/JSON Schema) with compatibility checks (BACKWARD/FORWARD/FULL) enforced in CI.
- Breaking change → new event **type/version** (`OrderPlaced.v2`); **upcasting** transforms old stored events to the new shape on read.
- Include `schemaVersion` in the envelope; consumers ignore unknown fields (tolerant reader).

## Gotchas -> Fix
- **Dual-write** (DB commit + broker publish as two steps) -> transactional **outbox** + relay/CDC; consumers dedupe.
- **Out-of-order events** (consumer assumes arrival order) -> partition by aggregate key; carry version/sequence numbers; ignore stale, buffer/park gaps.
- **Poison messages** (one bad event blocks the partition/queue forever, or crash-loops the consumer) -> retry with backoff, then route to a **dead-letter queue** with the failure context; alert and quarantine, don't block the stream.
- **Non-idempotent consumers** (double-processing double-charges) -> dedupe by event id / upsert / conditional writes; keep a processed-events table.
- **Event schema drift** (producer changes shape, consumers break) -> schema registry + compatibility gate in CI; additive changes only; version + upcast for breaks.
- **Treating events as commands** (one specific consumer, expecting a reply) -> if you need a directed request/response, use a command/RPC; keep events as fire-and-forget facts.
- **Fat vs thin trade-off ignored** (notification causes callback storms back on producer) -> switch to event-carried state transfer for hot paths; keep local read copies.
- **Eventual consistency surprises** (UI/read expects instant write visibility) -> design for lag: optimistic UI, read-your-writes, "pending" states; put hard invariants inside one aggregate.
- **No correlation/causation ids** -> can't trace a business flow across events; stamp `correlationId` + `causationId` in every envelope.
- **Unbounded event log / no snapshots** (event-sourced replay grows unbounded) -> periodic snapshots; archive/compact old streams.
- **Lost events on consumer restart** (auto-ack before processing) -> ack only after successful processing (at-least-once); design idempotency to absorb the resulting redeliveries.
- **Ordering assumed across topics/partitions** -> only intra-partition order is guaranteed; co-locate causally-related events by key or make consumers order-tolerant.
- **Event as integration backdoor** (consumers reach into internal fields never meant as contract) -> publish explicit, documented **domain events** distinct from internal state; don't leak the write model.
