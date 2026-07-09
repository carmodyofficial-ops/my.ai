# Kafka Streaming

## Core Model
- **Topic**: named append-only log, split into **partitions**. Partition = ordered, immutable sequence; unit of parallelism + ordering.
- **Offset**: monotonic per-partition message index. Consumers track position by offset.
- **Ordering guaranteed only within a partition**, never across a topic.
- **Replication factor** (e.g. 3): copies per partition across brokers. One **leader** handles reads/writes; **followers** replicate. **ISR** = in-sync replicas.
- **Key** decides partition: `hash(key) % numPartitions`. Same key → same partition → ordered. Null key → round-robin/sticky.
- Partition count sets max consumer parallelism in a group; you can increase but not decrease, and increasing breaks key→partition mapping.

## Producers
- `acks`: `0` (fire-forget, may lose), `1` (leader only, loses on leader failover), `all`/`-1` (all ISR ack — durable). Use `acks=all` for no loss.
- **Idempotent producer** (`enable.idempotence=true`, default in modern Kafka): dedupes retries via producer ID + sequence number → exactly-once *per partition* on produce. Requires `acks=all`.
- `retries` + `delivery.timeout.ms` govern resend. With idempotence, retries are safe.
- **Batching**: `linger.ms` (wait to fill batch) + `batch.size` + `compression.type` (lz4/zstd/snappy) → throughput. `max.in.flight.requests<=5` to keep ordering with idempotence.
- **Transactions** (`transactional.id`): atomic multi-partition writes + consumer-offset commit → exactly-once end-to-end with `read_committed` consumers.

## Consumers + Groups
- **Consumer group**: consumers sharing a `group.id` split partitions — each partition assigned to exactly one member. Adding members up to partition count scales; beyond that they idle.
- **Rebalancing**: reassigns partitions when members join/leave or partitions change. Stop-the-world (eager) pauses all; use **cooperative/incremental** (`CooperativeStickyAssignor`) to minimize disruption.
- **Offset commit**: `enable.auto.commit` (periodic, at-least-once, risk of loss/dupe) vs manual `commitSync`/`commitAsync` after processing (safer). Commit **after** processing for at-least-once.
- `max.poll.records` + `max.poll.interval.ms`: if processing a poll batch exceeds interval → consumer deemed dead → rebalance storm. Reduce batch or raise interval.
- `session.timeout.ms` + heartbeat govern liveness.

## Delivery Semantics
- **At-most-once**: commit offset before processing → lose on crash.
- **At-least-once** (default/common): process then commit → duplicates on retry. Make consumers **idempotent** (dedupe by key/offset).
- **Exactly-once (EOS)**: idempotent producer + transactions + `isolation.level=read_committed`; or Kafka Streams with `processing.guarantee=exactly_once_v2`. Only within Kafka boundaries; external sinks need idempotent/transactional writes.

## Retention + Compaction
- **Time/size retention**: `retention.ms`, `retention.bytes` — delete old segments regardless of key. Default log.
- **Log compaction** (`cleanup.policy=compact`): keeps latest value per key → changelog/table semantics (KTable, state restore). Tombstone (null value) deletes a key.
- Can combine `compact,delete`.

## Kafka Connect
- Framework for scalable, config-driven integration. **Source** connectors ingest into Kafka; **sink** connectors export out (JDBC, S3, Elasticsearch, Debezium CDC).
- Runs workers in distributed mode; handles offset tracking, restarts, scaling via tasks. Prefer over hand-rolled producers/consumers for standard systems.

## Streams / ksqlDB
- **Kafka Streams**: JVM library for stateful stream processing (map/filter/join/aggregate/windowing) with local state stores (RocksDB) backed by changelog topics; EOS support. KStream (events) vs KTable (compacted state).
- **ksqlDB**: SQL over streams/tables on top of Streams.

## Schema Registry (Avro/Protobuf/JSON)
- Central store of schemas; messages carry a schema ID, not the schema. Enforces **compatibility** (backward/forward/full) on register.
- Backward-compatible changes (add optional/defaulted field) let consumers upgrade independently. Prevents producer breaking consumers.

## Tuning
- **Throughput**: more partitions, batching (`linger.ms` 5–100, larger `batch.size`), compression (zstd/lz4), `acks=1` if some loss tolerable.
- **Latency**: `linger.ms=0`, smaller batches, fewer replicas to ack.
- **Consumer throughput**: scale partitions + group members, increase `fetch.min.bytes`/`max.partition.fetch.bytes`, parallelize processing.
- Size partitions for target parallelism up front (hard to shrink).

## Architecture Internals
- **Broker**: server holding partition replicas, serving produce/fetch. Cluster = many brokers.
- **Controller**: one broker coordinating leader election + metadata. **KRaft** mode (Kafka 3.x+) replaces ZooKeeper with an internal Raft quorum — no external ZK.
- **Segments**: partition log split into segment files; retention/compaction operate per-segment. **Page cache** serves hot reads → sequential IO + zero-copy = high throughput.
- **min.insync.replicas**: with `acks=all`, write succeeds only if this many replicas ack. RF=3 + `min.insync.replicas=2` tolerates one broker down without loss.
- **Leader epoch / high watermark**: consumers only read up to the high watermark (fully replicated offset).

## Consumer Mechanics
- **Poll loop**: `poll(timeout)` returns a batch; process; commit. Must call `poll` within `max.poll.interval.ms` to stay alive (also drives heartbeats in background thread).
- **Assignment**: `subscribe(topics)` = group-managed (auto rebalance) vs `assign(partitions)` = manual (no group, you own offsets).
- **Seek**: `seekToBeginning`, `seek(offset)` for replay/reprocessing. Reset with `auto.offset.reset` = `earliest`/`latest`/`none` when no committed offset.
- **`__consumer_offsets`**: internal compacted topic storing committed offsets per group/partition.

## Partition Sizing + Keys
- Partitions = parallelism unit. Plan for peak consumer count; over-provision modestly (more partitions = more open files/metadata, longer failover).
- Key selection controls ordering + distribution. High-cardinality, evenly-distributed key → balanced load with per-key ordering.
- To preserve ordering AND parallelism, key by the entity that needs ordering (e.g. `account_id`), not a global constant.

## Monitoring
- **Consumer lag** (log-end-offset − committed-offset) = the key health metric; rising lag = under-provisioned/slow consumers.
- Watch under-replicated partitions, offline partitions, ISR shrink, request latency, broker disk.
- `kafka-consumer-groups --describe` shows per-partition lag + assignment.

## Ordering + Idempotency Recap
- Order is per-partition only; to keep entity order, key by that entity and never rely on cross-partition order.
- Idempotent consumer: dedupe by `(topic, partition, offset)` or business key in the sink; makes at-least-once effectively once.
- Exactly-once inside Kafka: transactions + `read_committed`; across a boundary: idempotent/transactional sink required.

## Gotchas -> Fix
- **Rebalancing storm** (slow processing exceeds `max.poll.interval.ms`) → reduce `max.poll.records`, offload work, raise interval; use cooperative assignor.
- **Key skew** (one key = hot partition) → uneven load/lag → change key, add composite/random salt where ordering-per-key not required.
- **Poison message** stalls partition (repeated failure never advances offset) → try/catch + route to **dead-letter topic**, then commit past it.
- **Data loss with `acks=1`** on leader failover → use `acks=all` + `min.insync.replicas>=2` + RF>=3.
- **Duplicate processing** (at-least-once) → make consumer idempotent (dedupe by key/offset) or use EOS/transactions.
- **Offset commit before processing** → silent loss on crash → commit after processing.
- **Can't scale consumers past partition count** → idle members → increase partitions (plan ahead; breaks key locality).
- **Auto-commit dupes/loss** → switch to manual commit around processing.
- **Adding partitions breaks ordering** for existing keys → repartition mapping changes; avoid or accept reordering.
- **Unbounded consumer lag** → under-provisioned consumers or slow sink → scale group, batch writes, monitor lag (`consumer group lag`).
- **Large messages** → broker `message.max.bytes` + consumer fetch limits must match, else stuck → externalize big payloads (claim-check) or raise limits consistently.
- **EOS assumed for external DB sink** → Kafka transactions don't cover it → make sink idempotent (upsert on key).
- **Compacted topic used as event log** → intermediate updates lost (only latest/key kept) → use `delete` retention for event history, `compact` only for state/changelog.
- **Retention too short** vs consumer downtime → consumer resumes past-deleted offset → `OffsetOutOfRange` + data gap → size `retention.ms` above max expected consumer downtime.
- **Too many partitions** → longer failover, more open files, controller load → provision for real parallelism, not "just in case."
- **Uneven partitions from low-cardinality key** → hot broker → higher-cardinality or composite key.
- **Producer `max.in.flight>1` without idempotence + retries** → reordering on retry → enable idempotence (bounds in-flight to 5, preserves order).

## Common Configs (quick ref)
- Producer: `acks=all`, `enable.idempotence=true`, `linger.ms=20`, `compression.type=zstd`, `batch.size=64KB`.
- Consumer: `enable.auto.commit=false`, `max.poll.records=500`, `isolation.level=read_committed` (for EOS), `auto.offset.reset=earliest`.
- Topic: `retention.ms`, `cleanup.policy`, `min.insync.replicas=2`, `partitions`, `replication.factor=3`.
