# NoSQL Patterns

Design **from access patterns**, not from entities. NoSQL trades joins/flexible queries for scale + predictable latency.

## Families
- **Key-value** (Redis, DynamoDB, Riak): get/put by key. Fastest, simplest; no queries beyond key. Cache, sessions, profiles.
- **Document** (MongoDB, Couchbase, DynamoDB): JSON/BSON docs, secondary indexes, nested query. Semi-structured, evolving schema.
- **Wide-column** (Cassandra, ScyllaDB, HBase, Bigtable): rows keyed by partition, sparse columns, query-driven tables. Massive write throughput, time-series, huge scale.
- **Graph** (Neo4j, Neptune): nodes+edges, traversal queries. Relationships-first (social, fraud, recommendations).

## CAP & consistency
- **CAP**: on network **P**artition, choose **C**onsistency or **A**vailability. (No partition → both.)
- **CP** (Mongo primary, HBase): reject/stall on partition to stay consistent. **AP** (Cassandra, Dynamo): serve possibly-stale, converge later.
- **PACELC**: Else (no partition) trade Latency vs Consistency. Dynamo/Cassandra = AP/EL (low latency, eventual).
- **Consistency models**: strong (read sees latest write), **eventual** (converges), read-your-writes, monotonic, causal.
- Cassandra **tunable consistency**: `R + W > N` = strong (e.g. N=3, W=QUORUM(2), R=QUORUM(2)). `ONE/QUORUM/ALL`.

## Access-pattern-first design
1. List every query/write the app needs (+ frequency, latency SLA).
2. Model tables/keys so each pattern is a **single-partition lookup** (no scans, no cross-partition joins).
3. Duplicate/denormalize data across tables — one table per access pattern is normal.
- Writes are cheap; reads must be O(1)/single-partition. Storage is cheap; latency isn't.

## DynamoDB single-table design
- **PK (partition key)** = hash → which partition. **SK (sort key)** → order + range within partition. Composite key `PK+SK` uniquely identifies item.
- **Single-table**: multiple entity types in one table, overloaded generic `PK`/`SK` (e.g. `PK=USER#123`, `SK=ORDER#456`), item collections co-located for one-query fetch.
- **GSI** (global secondary index): different PK/SK, own partitions, **eventually consistent**, own capacity — enables new access patterns. **LSI**: same PK, alt SK, strongly consistent, defined at create only.
- Query = `PK =` + optional `SK` condition (`begins_with`, `between`); **never Scan** in prod paths.
- Capacity: on-demand vs provisioned; hot partition throttles.

## Cassandra data modeling
- **Partition key** (1st part of PRIMARY KEY) → node placement; **clustering keys** → sort within partition.
  `PRIMARY KEY ((user_id), event_time)` → partition user_id, rows sorted by event_time.
- One table per query; denormalize + duplicate writes. `WHERE` must include full partition key; range/order only on clustering cols.
- Avoid: `ALLOW FILTERING`, secondary indexes on high-cardinality, cross-partition queries.

## Denormalization & duplication
- Store the same data shaped per query (materialized views / write fan-out). Update all copies on write (app-managed or CDC).
- Accept redundancy + eventual consistency as the cost of scale.

## When NoSQL vs SQL
- **NoSQL**: known fixed access patterns, huge scale/write volume, horizontal scale, flexible/evolving schema, low-latency KV, geo-distribution.
- **SQL**: ad-hoc queries, multi-entity joins, strong ACID transactions, complex integrity/reporting, unknown future queries. Default to SQL unless you have a scale/pattern reason.

## DynamoDB operations detail
- **Conditional writes** for optimistic concurrency: `ConditionExpression="attribute_not_exists(PK)"` / `version = :v` → prevents lost updates, atomic.
- **Atomic counters**: `UpdateExpression="SET n = n + :inc"`. **TransactWriteItems**: up to 100 items ACID across tables.
- **Streams** (change data capture) → Lambda for fan-out/materialized views/replication.
- **TTL** attribute auto-expires items (~48h lag, free). **BatchGetItem/BatchWriteItem** for throughput.
- Capacity: partition ≈ 3000 RCU / 1000 WCU; adaptive capacity spreads hot keys but has limits.

## Consistency & replication patterns
- **Quorum** reads/writes (Dynamo-style): tunable `N` replicas, `R`+`W`. **Read repair** + **anti-entropy** (Merkle trees) heal divergence. **Hinted handoff** buffers writes for down nodes.
- **Vector clocks / last-write-wins** conflict resolution (Cassandra = LWW by timestamp → clock skew can silently drop writes).
- **Idempotency**: since retries + at-least-once are common, use idempotency keys / conditional writes.
- **Materialized view / CDC**: write base table → stream → derive query-optimized copies asynchronously (eventual).

## Graph & document notes
- Graph: model when queries are multi-hop traversals (friends-of-friends, shortest path); relational JOINs blow up at depth.
- Document: secondary indexes + rich queries, but still design around dominant access patterns; avoid unbounded arrays.

## Gotchas -> Fix
- **Hot partition** (celebrity key, sequential/low-cardinality PK, `PK=STATUS`) → throttling, one node overloaded. Fix: high-cardinality partition key, add suffix/sharding (`PK#0..N`), write-sharding, distribute by hash.
- **Unbounded partition** (all events under one PK grows forever) → huge partition, timeouts (Cassandra: keep < ~100MB/100k rows). Fix: add time bucket to partition key (`(sensor_id, day)`), cap partition size.
- **Missing access pattern discovered late** → data un-queryable without full scan/migration. Fix: enumerate patterns up front; add GSI / new denormalized table + backfill.
- **Using Scan/`ALLOW FILTERING`** in hot path → full-table cost, throttling. Fix: model a table/index so it's a partition-key query.
- **Assuming GSI is strongly consistent** → stale reads after write. Fix: read base table for strong consistency; tolerate eventual on GSI.
- **Modeling relationally then porting** (normalized tables + app-side joins) → N+1, slow. Fix: redesign around queries, embed/duplicate.
- **Cross-partition transactions expected** → not supported / expensive. Fix: keep transactional data in one partition/item; use single-item conditional writes; idempotency.
- **Large item / doc** (DynamoDB 400KB item, hot large doc) → cost, throttle. Fix: split, store blob in S3 + pointer.
- **Tombstone buildup** (Cassandra deletes) → read latency. Fix: TTL-based expiry, avoid delete-heavy patterns, tune gc_grace.
- **Eventual consistency surprises** (read-after-write missing). Fix: strongly-consistent read option where supported; read-your-writes routing; design UI for it.
- **Clock-skew LWW data loss** (Cassandra last-write-wins drops a concurrent write). Fix: NTP sync, avoid concurrent updates to same cell, use CRDTs / app-level merge / append-only.
- **Denormalized copies drift** (updated one table, not the duplicate). Fix: single write path / CDC-driven updates; reconciliation jobs; idempotent updates.
- **Secondary index misuse** (Cassandra 2i on high-cardinality or low-cardinality) → scatter-gather across nodes. Fix: model a query table; materialized views for known patterns.
- **Batch misused as transaction** (Cassandra `BATCH` across partitions) → coordinator pressure, not atomic across partitions. Fix: single-partition batches only; keep batches small.

## When to reach for each family
- **Key-value**: session/cache/config, simple by-id lookups, extreme throughput.
- **Document**: content, catalogs, user profiles, evolving semi-structured data with secondary queries.
- **Wide-column**: time-series, event logs, IoT, write-heavy at massive scale, known query shapes.
- **Graph**: relationship traversals, recommendations, fraud rings, knowledge graphs.
- **Relational (default)**: transactions, ad-hoc queries, reporting, referential integrity, unknown future access patterns. Many systems are **polyglot** — SQL for source of truth + Redis/search/vector for specialized reads.

## Access-pattern worksheet (do this first)
- Enumerate: entity, operation (read/write), filter keys, sort, cardinality, frequency, latency SLA, consistency need.
- Map each to a single-partition primary key or GSI/materialized table. If a pattern needs a scan, redesign the key.
- Estimate item/partition size growth over time → add time/hash buckets to keep partitions bounded.
