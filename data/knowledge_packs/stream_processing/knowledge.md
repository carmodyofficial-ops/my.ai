# Stream Processing

## Batch vs stream
- **Batch**: bounded, finite dataset processed to completion; high throughput, high latency, reprocess-friendly.
- **Stream**: unbounded, continuous events processed as they arrive; low latency, incremental state, "never finishes." Batch is a special (bounded) case of streaming (Flink treats it that way).
- Micro-batch (Spark Structured Streaming) processes small batches on an interval — a middle ground with higher latency than true event-at-a-time (Flink).

## Time semantics (the crux)
- **Event time**: when the event actually occurred (embedded timestamp). Correct, deterministic, replay-safe — reprocessing gives identical results.
- **Processing time**: when the operator observes it (wall clock). Simple, low-latency, but non-deterministic and wrong under delays/backfills.
- **Ingestion time**: timestamp assigned at source entry (compromise).
- **Always prefer event time** for correctness; use processing time only for latency-critical, order-insensitive cases.

## Watermarks & late data
- A **watermark** is a moving threshold asserting "no more events with timestamp <= W will arrive" — it drives when event-time windows *fire*. Watermark = max-seen-event-time − allowed-lateness bound.
- Trade-off: aggressive (small delay) watermark = low latency but more late/dropped events; conservative = higher latency, fewer drops.
- **Late data** = event arriving after the watermark passed its window. Options: drop (default), route to a **side output** (Flink `sideOutputLateData`), or allow re-firing with `allowedLateness` (keeps window state longer, emits updates).
- Flink: `WatermarkStrategy.forBoundedOutOfOrderness(Duration.ofSeconds(10))` + `withTimestampAssigner`. Per-partition watermarks; the operator watermark = **min** across inputs -> one idle/lagging partition stalls progress (`withIdleness` to skip idle sources).

## Windowing
- **Tumbling**: fixed-size, non-overlapping, contiguous (e.g. every 1 min). Each event in exactly one window.
- **Sliding/hopping**: fixed size + slide interval; overlapping (size 10m, slide 1m -> each event in 10 windows). More output, more compute.
- **Session**: dynamic, gap-based; closes after an inactivity gap (e.g. 30 min idle). Windows merge as events arrive.
- **Global/count**: all events into one window, fired by a custom trigger (e.g. every N elements).
- Windows fire on watermark (event time) or timer; triggers can emit early/late results (incremental).

## Stateful processing & state backends
- Operators keep **keyed state** (per-key aggregates, joins, dedup, pattern buffers) partitioned by key. State is the hard part of streaming.
- Flink state: `ValueState`, `ListState`, `MapState`, `ReducingState`, `AggregatingState`; access only in a keyed context.
- **State backends**: Flink HashMapState (on-heap, fast, size-bounded by RAM) vs **RocksDB** (on-disk, spills, supports huge state + incremental checkpoints). Kafka Streams uses embedded **RocksDB** stores backed by compacted **changelog topics** for recovery.
- **TTL / retention** on state is mandatory for unbounded keyspaces (see gotchas).

## Exactly-once & checkpointing
- **Checkpointing** (Flink): periodic asynchronous **distributed snapshots** (Chandy-Lamport barriers flow through the graph) of all operator state -> durable store (S3/HDFS). On failure, restore last checkpoint + rewind source offsets -> **exactly-once state**.
- **End-to-end exactly-once** needs a transactional/idempotent sink (two-phase commit): Kafka transactions, or idempotent upserts keyed by event id. Without it you get *effectively-once* state but at-least-once *output*.
- **Savepoints** (Flink): manually triggered, self-contained snapshots for upgrades/rescaling/migration; keep them across job versions (checkpoints are for auto-recovery, savepoints for humans).
- Kafka Streams `processing.guarantee=exactly_once_v2` uses Kafka transactions + offset commits atomically.

## Kafka Streams
- Library (not a cluster) embedded in your app; scales by partition count; state co-located with the app instance.
- **KStream** = unbounded record stream (append, event log). **KTable** = changelog/compacted view (latest value per key, upsert). **GlobalKTable** = fully replicated (broadcast join, no co-partition needed).
- **Stream-table duality**: a stream aggregated -> table; a table's changelog -> stream. `groupByKey().aggregate()/count()/reduce()` -> KTable.
- Joins: KStream-KStream = **windowed** join (both need a window). KStream-KTable = lookup/enrichment (no window). Stream-table and table-table joins require **co-partitioning** (same key + partition count) unless GlobalKTable.
- Repartitioning triggered by key changes creates internal topics; rebalancing moves partitions + restores state from changelog.

## Apache Flink
- **DataStream API**: `source -> transform -> sink`. Operators: `map`, `flatMap`, `filter`, `keyBy` (partition by key), `window`, `reduce/aggregate/process`, `connect`/`union`, `CoProcessFunction`.
- `ProcessFunction` = low-level: event access + registered **event-time/processing-time timers** + side outputs. `keyBy` before any keyed state/window.
- Table API / Flink SQL for declarative; CDC connectors; unified batch+stream runtime.

## Other essentials
- **Backpressure**: slow downstream -> buffers fill -> upstream throttles automatically (Flink credit-based flow control). Sustained backpressure = under-provisioned operator/skew; monitor it as a health signal.
- **Out-of-order** handled via event time + watermarks + allowedLateness (not by assuming ordering).
- **CEP** (Complex Event Processing): detect patterns/sequences over streams (Flink CEP `Pattern.begin().followedBy()...within(time)`) — fraud, monitoring.
- **Data skew**: hot keys overload one partition/operator -> pre-aggregate, salt keys, or two-phase aggregation.

## Triggers, retention & emission
- **Triggers** decide *when* a window emits (independent of the window definition): on-watermark (default, one final result), early firing (`ContinuousProcessingTime`/count triggers for partial results), late firing (on late data with allowedLateness). Beam formalizes this (accumulating vs discarding panes).
- Emit modes: **accumulating** (each fire re-emits the full aggregate, downstream must upsert/dedupe) vs **discarding** (each fire emits only the delta). Pick based on sink semantics.
- Retention: window state is held until watermark > windowEnd + allowedLateness, then purged. Long lateness + many overlapping sliding windows = large state.

## Delivery semantics & sinks
- **At-most-once** (fire-and-forget, may drop), **at-least-once** (may duplicate, needs idempotent consumer), **exactly-once** (state-consistent). Most real pipelines: at-least-once transport + idempotent/transactional sink = effectively-once.
- Idempotent sink patterns: upsert keyed by a deterministic event id; dedup table/bloom filter; Kafka transactions (`transactional.id`); DB `INSERT ... ON CONFLICT`. Sink must be replay-safe because recovery re-emits from the last checkpoint.
- Source must support **replay** (offset rewind) for exactly-once — Kafka/Kinesis/Pulsar do; a non-replayable source caps you at at-most-once on failure.

## Scaling & operations
- Parallelism = partitions (Kafka) or operator subtasks (Flink); **max parallelism** in Flink is fixed at first run (key-group count) — set it high enough up front or you can't rescale via savepoint.
- Rescale Flink: stop-with-savepoint -> restart with new parallelism from savepoint. Kafka Streams scales by adding instances (bounded by input partition count) with cooperative rebalancing.
- Monitor: consumer/operator **lag** (records behind), backpressure %, checkpoint duration/size/failures, state size growth, watermark lag, restart count. Lag trending up = under-provisioned or skewed.

## Gotchas -> Fix
- **Event-time vs processing-time confusion** -> windows never fire or fire wrong -> assign event-time timestamps + a `WatermarkStrategy`; verify records carry a monotonic-ish timestamp; don't mix time characteristics.
- **Windows never fire / no output** -> watermark not advancing: an **idle or empty partition**, or no timestamp assigner -> add `withIdleness(...)`, ensure every source partition gets data or is marked idle; check watermark metric per operator.
- **Unbounded state growth / OOM** -> keyed state for an ever-growing keyspace (per-user, per-session) with no cleanup -> set **state TTL**, use session windows with gaps, RocksDB backend + incremental checkpoints, and clear timers in `ProcessFunction`.
- **Watermark tuning wrong** -> too tight drops legitimate late events; too loose adds latency + holds state -> measure real event lateness distribution, set `forBoundedOutOfOrderness` to ~p99 lateness, capture drops via side output to quantify.
- **Late data silently dropped** -> default behavior discards post-watermark events -> add `allowedLateness` (emit updates) and/or `sideOutputLateData` to a dead-letter stream; account for downstream idempotency of re-fires.
- **Rebalancing storms / long recovery** -> Kafka Streams/consumer group churn triggers full state restore from changelog -> use `static membership` (`group.instance.id`), standby replicas (`num.standby.replicas`), cooperative rebalancing, and RocksDB to bound restore time.
- **"Exactly-once" myth** -> config'd EO but sink still duplicates -> exactly-once is *state* consistency; end-to-end needs a transactional/idempotent sink (Kafka txn / upsert by key). At-least-once + idempotent writes is often simpler and sufficient.
- **Checkpoints too frequent/slow -> backpressure** -> large sync state snapshots stall the pipeline -> enable async + **incremental** checkpoints (RocksDB), tune interval/timeout, use unaligned checkpoints under backpressure; increase `min.pause.between.checkpoints`.
- **Join produces nothing** (Kafka Streams) -> inputs not co-partitioned (different key/partition count) or window too small -> repartition to same key+partitions, widen join window, or use a GlobalKTable for lookups.
- **Non-determinism on reprocess** -> logic uses processing time / `System.currentTimeMillis()` / wall-clock windows -> use event time everywhere for replayable, deterministic results.
- **Sustained backpressure ignored** -> a skewed/hot operator silently caps throughput -> monitor backpressure + per-key load; fix skew (salting/two-phase agg), scale the bottleneck operator's parallelism.
- **State schema change breaks restore** -> altered state types can't restore from savepoint -> use schema-evolution-friendly serializers (Avro/POJO), migrate via savepoint, version state.
