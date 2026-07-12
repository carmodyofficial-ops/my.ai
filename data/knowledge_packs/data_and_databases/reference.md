# Data & Databases Cheat-Sheet

For engine specifics see packs: **postgresql**, **mongodb**, etc.

## Pick the store
- **Relational (Postgres/MySQL)**: default. Strong schema, joins, ACID, constraints. OLTP + most apps.
- **Document (MongoDB)**: flexible/nested schema, high write throughput, denormalized read models; weak cross-doc joins/transactions (improving). Good when access is by aggregate/key.
- **Key-value (Redis/DynamoDB)**: O(1) get/set by key, caching, sessions, queues; no ad-hoc queries.
- **Wide-column (Cassandra)**: massive write scale, query-driven denormalized tables, tunable consistency.
- **Analytical / columnar (BigQuery, Snowflake, ClickHouse, DuckDB)**: OLAP — scan/aggregate huge tables; column storage; not for row-level OLTP.
- **Search (Elasticsearch)**: full-text/relevance. **Graph (Neo4j)**: relationship traversal.
- Rule: start relational; add a specialized store only for a **measured** need. Fewer stores = fewer consistency headaches.

## ACID vs BASE, CAP
- **ACID** (relational): Atomicity, Consistency, Isolation, Durability — correctness first.
- **BASE** (many NoSQL): Basically Available, Soft state, Eventual consistency — availability/scale first.
- **CAP**: under a network partition you choose Consistency **or** Availability (not both). Most distributed DBs are CP or AP; single-node relational sidesteps it. "Eventually consistent" = reads may be stale.

## OLTP vs OLAP
- **OLTP**: many small point reads/writes, low latency, normalized, row store, indexed by PK/FK. App backends.
- **OLAP**: few large scan/aggregate queries, columnar, denormalized star/snowflake schema, batch/stream loaded. Analytics/BI.
- Don't run heavy analytics on the OLTP primary — replicate/ETL to a warehouse.

## Schema & modeling
- Normalize by default (3NF): every non-key fact depends on the key, the whole key, nothing but the key. Denormalize only for measured read hotspots — and keep a source of truth.
- Stable surrogate PK (`BIGINT` autoinc or UUID); never a mutable natural key. Sequential IDs pack better in indexes; random UUIDv4 fragments B-tree inserts (prefer UUIDv7/ULID if you need UUIDs).
- `NOT NULL` + sane `DEFAULT` where possible; NULL = "unknown", not 0/"". Enforce invariants in the DB (FK, `UNIQUE`, `CHECK`), not just app code.
- Model documents around access patterns (embed for read-together, reference for large/shared/independently-updated data).

## Indexing
- Index columns you filter/join/sort by; FKs need their own index (not auto in Postgres). Composite index column order = **equality first, then range/sort**; leftmost-prefix rule governs which queries it serves.
- Covering index (`INCLUDE`) answers a query from the index alone. Partial index for a hot subset. Don't over-index: each index slows writes and costs storage.
- Read `EXPLAIN (ANALYZE)`; a seq scan on a big filtered table = missing/unused index (watch for functions on the column or type mismatch defeating the index).

## Queries & optimization
- ALWAYS parameterize: `execute("...WHERE id=?", (id,))`. Never f-string/`%`-format SQL -> injection.
- **N+1**: a query per row in a loop. Fix: one JOIN / `WHERE id IN (...)` / ORM eager load (`selectinload`/`joinedload`, Django `select_related`/`prefetch_related`).
- Prefer JOIN over correlated subquery; window functions over self-joins. `SELECT` only needed columns. Keyset (`WHERE id > :last`) beats `OFFSET` for deep pagination.
- `COUNT(*)` counts rows; `COUNT(col)` skips NULLs. `x = NULL` is never true -> `IS NULL`.

## Transactions & isolation
- Wrap multi-write logic in one transaction; commit once, rollback on error (atomicity). Keep transactions short — long ones bloat locks/MVCC.
- Isolation levels (weakest->strongest): Read Uncommitted, Read Committed (Postgres default), Repeatable Read, Serializable. Higher = fewer anomalies (dirty/non-repeatable/phantom reads), more contention.
- Row locks: `SELECT ... FOR UPDATE` to serialize concurrent updates. Avoid deadlocks by locking rows in a consistent order.

## Scaling: replication, partitioning, sharding
- **Replication**: primary + read replicas (scale reads/HA). Async replicas can serve **stale** reads; sync trades latency for freshness. Failover promotes a replica.
- **Partitioning**: split one table by range/list/hash within a DB (prune scans, drop old partitions cheaply).
- **Sharding**: split data across nodes by a shard key (horizontal write scale). Costs: cross-shard joins/transactions are hard; pick a shard key that spreads load and matches queries. Do it only when vertical scaling + replicas are exhausted.

## Ops: pooling, migrations, backups
- **Connection pooling** (PgBouncer / app pool): reuse connections; each Postgres connection is a process — thousands of raw connections exhaust it. Size the pool; set statement/idle timeouts.
- **Migrations**: version-controlled, expand/contract for zero downtime — 1) add nullable col/new table (additive), 2) backfill in batches, 3) switch app read/write, 4) add `NOT NULL`/drop old later. Never rename+drop in one deploy (old code still runs). Review autogenerated migrations — tools miss renames, server defaults, enum/type changes. Add indexes `CONCURRENTLY` (Postgres) to avoid table locks.
- **Backups**: automated + **tested restores** (an untested backup is not a backup). Know your RPO (data-loss window) / RTO (recovery time). Combine periodic full dumps + PITR (WAL/binlog). Keep off-site copies.

## Time & JSON
- Store UTC (`TIMESTAMPTZ`); convert at display edge — never store naive local time.
- JSON/JSONB for sparse/flexible data; index with expression/GIN. Don't put queried-by-key fields in JSON — promote to real columns.

## Gotchas -> Fix
- Missing indexes on filter/join/FK columns -> full scans; add indexes, verify with `EXPLAIN ANALYZE`.
- No/untested backups -> unrecoverable loss; automate + rehearse restores; monitor replication lag.
- Wrong isolation -> lost updates/phantoms under concurrency; raise level or use `FOR UPDATE`/optimistic version column.
- Unbounded growth -> tables/logs/queues grow forever; add retention, partition + drop old, archive cold data.
- N+1 queries -> batch/JOIN/eager-load.
- SQL built by string concat -> injection; parameterize.
- Long/leaked transactions & connections -> lock bloat, pool exhaustion; keep txns short, pool + timeout, close/return connections.
- Editing an applied migration or big-bang schema change -> drift/downtime; new migration + expand/contract.
- Over-indexing -> slow writes; index for real query patterns only.
- Analytics on OLTP primary -> contention; use a replica/warehouse.
