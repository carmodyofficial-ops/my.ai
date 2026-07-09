# Message Queues

## Queue vs pub/sub vs stream
- **Queue (point-to-point)**: each message consumed by **exactly one** worker among competing consumers. Message is removed after ack. Use for **work distribution / task offloading** (jobs, emails). RabbitMQ queue, SQS.
- **Pub/Sub (fan-out)**: each message delivered to **every** subscriber. Publisher decoupled from N subscribers. Use for **event broadcast/notifications**. RabbitMQ topic/fanout exchange, SNS, Redis pub/sub (no persistence).
- **Stream (log)**: append-only, **retained** log; consumers read at their own offset and can **replay**. Multiple consumer groups read independently. Use for event sourcing, high-throughput pipelines, replay. Kafka, Kinesis, Redis Streams.
- Key distinction: queues **delete on consume**; streams **retain** and let consumers re-read.

## Brokers
- **RabbitMQ** (AMQP): rich routing via **exchanges** (direct/topic/fanout/headers) → bindings → queues. Per-message ack, DLX, priority, TTL, delayed messages. Great for complex routing + task queues; throughput lower than Kafka.
- **Amazon SQS**: managed. **Standard** (at-least-once, best-effort order, near-unlimited throughput) vs **FIFO** (exactly-once processing within a dedup window, strict order per **MessageGroupId**, ~300 TPS/3000 batched). Visibility timeout, DLQ via redrive policy.
- **ActiveMQ / Artemis** (JMS): classic Java broker, queues + topics, transactions.
- **Kafka / Pulsar**: partitioned streams, high throughput, retention/replay, consumer groups. (See kafka pack.)
- **Redis Streams**: lightweight streams with consumer groups (`XADD`/`XREADGROUP`/`XACK`), in-memory.

## Delivery guarantees
- **At-most-once**: ack before processing (or fire-and-forget) → may **lose** messages, never duplicates. Only for tolerable loss (metrics samples).
- **At-least-once** (the practical default): ack **after** successful processing → no loss, but **duplicates** on redelivery. Requires **idempotent consumers**.
- **Exactly-once**: no duplicates and no loss — impossible in general across process + broker + side effects. Approximated via at-least-once + idempotency/dedup, or transactional broker features (Kafka EOS within Kafka only). Treat vendor "exactly-once" as **exactly-once processing** under constraints, not magic.

## Ack / nack & redelivery
- Consumer **acks** to remove the message. **Nack/reject** with requeue=true redelivers; requeue=false drops or routes to DLQ.
- **Auto-ack is dangerous**: broker considers delivered before you've processed → crash = lost message. Use **manual ack after processing**.
- If a consumer dies before acking, the broker redelivers (that's why at-least-once → dupes). SQS uses a **visibility timeout**: message hidden while in-flight; if not deleted before timeout, it reappears.
- Ack the **specific delivery tag**; don't ack out of band or you'll lose/duplicate.

## DLQ, retry, backoff
- **Dead-letter queue**: destination for messages that repeatedly fail, exceed max-receives, expire (TTL), or are rejected. Prevents a bad message from blocking the queue forever.
- **Retry with backoff**: on transient failure, retry a few times with **exponential backoff + jitter**; after max attempts → DLQ with failure metadata (error, attempt count, stack). Immediate infinite requeue = **redelivery storm**.
- Pattern: primary queue → (fail) → retry/delay queue → (max) → DLQ; monitor + alert on DLQ depth; build a **redrive** path to replay fixed messages.
- Distinguish **transient** (retry: timeout, 503) from **permanent** (straight to DLQ: schema error, validation) failures — don't retry poison forever.

## Ordering
- Ordering is only guaranteed **per queue/partition/message-group**, never globally across parallel consumers.
- SQS **FIFO**: order + dedup **within a MessageGroupId**; different groups process in parallel. Standard SQS gives best-effort order only.
- RabbitMQ preserves order **within a single queue with a single consumer**; add competing consumers/prefetch>1 and order is lost.
- To keep related messages ordered, route them to the **same group/partition by key** — but that caps parallelism for that key.

## Idempotent consumers
- Since redelivery is inevitable, make processing **idempotent**: dedupe by a stable **message id / business key** (unique constraint, processed-ids table, upsert, conditional write).
- Store the idempotency key **in the same transaction** as the side effect where possible; otherwise a crash between "do work" and "record processed" re-does the work.
- Prefer naturally idempotent operations (set state = X) over non-idempotent ones (increment, append).

## Prefetch / backpressure / competing consumers
- **Prefetch (QoS)**: limit unacked messages per consumer (`prefetch_count`). Too high = one consumer hoards messages, uneven load, big loss window on crash; too low = idle round-trips. Tune to ~throughput × processing time.
- **Competing consumers**: scale out N workers on one queue for horizontal throughput; broker load-balances deliveries.
- **Backpressure**: bounded prefetch + bounded queue length + consumer-driven pull naturally throttle producers. Publisher confirms + flow control prevent overrun. Unbounded queues hide the fact you can't keep up.
- Watch **queue depth / consumer lag** as the primary saturation signal; scale consumers or shed load when it climbs.

## Priority & delay queues
- **Priority queues**: higher-priority messages jump ahead (RabbitMQ `x-max-priority`). Risk: **starvation** of low-priority; cap levels and reserve capacity.
- **Delay/scheduled**: deliver after a delay (SQS `DelaySeconds` ≤ 15 min, RabbitMQ delayed-message plugin or dead-letter-TTL trick). Use for retries with backoff, scheduled tasks, debouncing.

## Routing (RabbitMQ exchanges)
- Producers publish to an **exchange**, not directly to a queue; bindings route to queues by rule. Decouples producers from queue topology.
- **Direct**: route by exact routing key (`orders.paid` → the queue bound to that key). **Topic**: wildcard keys (`orders.*`, `orders.#`) for flexible subscription. **Fanout**: broadcast to all bound queues (ignore key). **Headers**: match on header attributes.
- **Dead-letter exchange (DLX)**: a queue's rejected/expired/overflow messages re-publish to a DLX → DLQ. **Alternate exchange**: catches unroutable messages.

## Publisher-side reliability
- **Publisher confirms** (Rabbit) / **acks** (Kafka `acks=all`): broker confirms durable receipt; without them a publish can be silently lost. Don't fire-and-forget critical messages.
- **Persistence/durability**: mark queues durable + messages persistent (Rabbit) or set replication factor + `min.insync.replicas` (Kafka); a non-durable queue loses messages on broker restart.
- **Transactions vs confirms**: confirms are far faster than AMQP transactions for durability; batch confirms for throughput.
- **Outbox pattern** on the producer avoids the dual-write (DB commit + publish) race — write the message to an outbox table in the same DB transaction, relay it to the broker asynchronously.

## Queue vs Kafka — when
- **Queue (Rabbit/SQS)** when: task/job distribution, per-message ack + redelivery + DLQ, complex routing, messages are consumed-and-gone, modest-to-high throughput. Once consumed, it's gone.
- **Kafka/stream** when: very high throughput, **retention + replay**, multiple independent consumer groups over the same data, event sourcing, ordered partitions, reprocessing history. No per-message ack/nack or arbitrary redelivery; consumers manage offsets.

## Gotchas -> Fix
- **Poison message** blocks the queue / crash-loops the consumer -> cap retries with backoff, then route to **DLQ** with error context; alert + quarantine; never infinite-requeue.
- **Redelivery storm** (immediate requeue on failure, thundering retries) -> exponential backoff + jitter, max attempts, delay/retry queue between primary and DLQ.
- **Lost acks / auto-ack** (crash after delivery, before processing) -> manual ack **after** successful processing; size prefetch/visibility timeout to bound the in-flight loss window.
- **Assuming global ordering** with multiple consumers/prefetch>1 -> order holds only per group/partition/single-consumer queue; partition by key if order matters, accept reduced parallelism.
- **Assuming exactly-once** -> design for at-least-once; make consumers idempotent (dedup by message id/business key).
- **Visibility timeout too short** (SQS) -> message reappears mid-processing → duplicate work; set timeout > max processing time or extend heartbeat.
- **Prefetch too high** -> one worker hoards the backlog, others idle, large loss on crash -> lower prefetch to fair-share.
- **Unbounded queue growth** hides consumer inability to keep up -> monitor depth/lag, add consumers, apply backpressure/load-shedding, set max-length + overflow-to-DLQ.
- **DLQ ignored** -> silent data loss piling up -> alert on DLQ depth, inspect, fix, and **redrive** replay.
- **Non-idempotent side effects** (double emails/charges on redelivery) -> idempotency keys + conditional writes; record processed id in the same transaction as the effect.
- **Priority starvation** -> reserve capacity/quotas for lower priorities; bound priority levels.
- **Redis pub/sub for durable messaging** -> it's fire-and-forget, no persistence; offline subscribers miss messages -> use Redis Streams or a durable broker.
