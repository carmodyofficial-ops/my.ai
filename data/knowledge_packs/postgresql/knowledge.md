# PostgreSQL-Specific Reference

## Types (prefer these)
- IDs: `GENERATED ALWAYS AS IDENTITY` (SQL-standard) over `serial`. Both use a sequence; **gaps are normal** (rollbacks/caching) — never assume contiguous.
- `bigint` for IDs/counts; `text` over `varchar(n)` (identical perf, no length guessing). `timestamptz` **always** over `timestamp` — stores UTC, renders per session `TimeZone`; `timestamp` drops offset -> silent bugs.
- `numeric(12,2)` for money (never float — rounding errors). `uuid` via `gen_random_uuid()` (pgcrypto/core PG13+). `boolean`.
- Arrays: `int[]`, `text[]` — literal `'{1,2}'`, `arr[1]` 1-based, membership `x = ANY(arr)`, `@>`/`&&` operators, GIN-indexable.
- Enums: `CREATE TYPE mood AS ENUM('lo','hi');` — compact, ordered; adding values is easy (`ALTER TYPE ... ADD VALUE`), **removing/reordering is not** — many prefer a `text` + `CHECK` or lookup table.
- `jsonb` (binary, indexable, dedup keys, no whitespace) over `json` (raw text, preserves order/dupes).

## JSONB
- `->` returns jsonb, `->>` returns text: `data->'a'->>'b'`. Path: `#>'{a,b}'`, `#>>`. SQL/JSON path: `jsonb_path_query(data,'$.a[*]')`.
- `@>` contains: `data @> '{"k":1}'`. `?` key exists, `?|`/`?&` any/all keys.
- Write: `jsonb_set(data,'{a,b}','5')`; merge `||`; delete key `data - 'k'`, path `#-'{a,b}'`.
- **GIN index required** for `@>`/`?`: `CREATE INDEX ON t USING gin (data);` — `jsonb_path_ops` variant is smaller/faster but only supports `@>`.
- Don't over-JSONB: relational columns for anything you filter/join/constrain heavily; JSONB for sparse/dynamic attrs.

## Indexes
- **B-tree** (default): `=`, `<`/`>`, ranges, `ORDER BY`, `LIKE 'x%'` (prefix, C locale or `text_pattern_ops`).
- **GIN**: jsonb, arrays, full-text (`tsvector`), trigram (`pg_trgm` for `LIKE '%x%'`). **GiST**: geometry, ranges, nearest-neighbor. **BRIN**: huge, physically-ordered append-only tables (time-series) — tiny index, block-range min/max.
- **Partial**: `CREATE INDEX ON t(x) WHERE active;` — smaller, indexes only hot rows. **Expression**: `CREATE INDEX ON t(lower(email));` — query must use the *same* expression to hit it.
- **Composite**: `(a,b)` serves `WHERE a=` and `WHERE a= AND b=` and `ORDER BY a,b`; leftmost-prefix rule — won't serve `WHERE b=` alone. **Covering**: `INCLUDE (c)` for index-only scans.
- `CREATE INDEX CONCURRENTLY` — no `ACCESS EXCLUSIVE` lock; **use in prod** (2 scans, slower, can't run inside a txn, may leave an `INVALID` index on failure -> `DROP` and retry).
- UNIQUE index enforces uniqueness + backs `ON CONFLICT`. Find unused: `pg_stat_user_indexes` (`idx_scan=0`).

## EXPLAIN / plans
- `EXPLAIN (ANALYZE, BUFFERS) SELECT ...` runs it, shows planned vs `actual` rows/time + shared/heap block reads. Add `FORMAT JSON` for tooling.
- **Seq Scan**: full table (optimal for small tables or when most rows match). **Index Scan** / **Index Only Scan** (no heap fetch, needs visibility map fresh via vacuum) / **Bitmap Heap Scan** (many scattered matches).
- Joins: **Nested Loop** (small outer + indexed inner), **Hash Join** (large equijoin), **Merge Join** (sorted). Big estimate vs `actual` gap => stale stats -> `ANALYZE t` (or raise `default_statistics_target`).
- `rows` off by 100x, `Rows Removed by Filter` huge, or unexpected Seq Scan => missing/unusable index or non-sargable predicate (function on the column, type mismatch).

## Upsert / RETURNING
```sql
INSERT INTO t(id,x) VALUES(1,5)
ON CONFLICT (id) DO UPDATE SET x = EXCLUDED.x
RETURNING id;
```
- Conflict target must be a unique constraint/index. `DO NOTHING` to ignore. `RETURNING *` on INSERT/UPDATE/DELETE.

## CTEs & Window functions
- `WITH x AS (...)` and `WITH RECURSIVE` (trees/graphs). CTEs **inline by default PG12+** (optimizer can push predicates); force a materialization barrier with `AS MATERIALIZED`, prevent with `NOT MATERIALIZED`.
- Windows: `row_number()/rank()/dense_rank()/lag()/lead()/sum() OVER (PARTITION BY a ORDER BY b)`. Frames: `ROWS BETWEEN ...`. `DISTINCT ON (a) ... ORDER BY a, ts DESC` (PG-only "latest per group").

## Transactions / MVCC / isolation
- MVCC: each row has `xmin`/`xmax`; readers see a snapshot, **never block writers, never block readers**. Cost: dead tuples.
- Isolation: **Read Committed** (default — each statement fresh snapshot), **Repeatable Read** (txn-level snapshot, no phantom for the snapshot), **Serializable** (SSI — may abort with `40001` serialization_failure; app must **retry**).
- `SELECT ... FOR UPDATE` locks rows; `FOR UPDATE SKIP LOCKED` = concurrent work queues; `FOR NO KEY UPDATE`/`FOR SHARE` weaker.

## Locks
- Row locks (writes) don't block reads. Table locks: `ALTER TABLE`, `VACUUM FULL`, `CREATE INDEX` (non-concurrent) take strong locks that block queries.
- Deadlocks auto-detected + one txn aborted (`40P01`) — always lock rows in a consistent order. Inspect: `pg_locks` joined to `pg_stat_activity`; `pg_blocking_pids(pid)`.
- A blocked DDL behind a long query can queue *everything* behind it (lock queue); set `lock_timeout`/`statement_timeout` before DDL.

## Partitioning
- Declarative: `PARTITION BY RANGE(created_at)` / `LIST` / `HASH`; attach child partitions. Planner **prunes** irrelevant partitions. Great for time-series + cheap drop-old (`DROP` partition vs mass DELETE).
- Indexes/constraints are per-partition; the partition key should be in most queries + must be in any unique constraint.

## Replication / WAL
- WAL = write-ahead log; every change logged before data pages (durability, crash recovery, replication). `synchronous_commit`, `wal_level=replica/logical`.
- **Streaming (physical) replication**: byte-identical read replicas, async by default (replica lag) or synchronous. **Logical replication**: publish/subscribe per-table (upgrades, selective/cross-version). PITR via base backup + WAL archive.

## Connection pooling
- Each connection = a backend **process** (~MBs) — hundreds exhaust RAM/CPU; `max_connections` default 100. App pool + **PgBouncer** in front.
- PgBouncer modes: `session` (per-client), `transaction` (per-txn — highest reuse, but **breaks** session state: prepared statements, `SET`, advisory locks, `LISTEN`), `statement`.

## Extensions / tuning
- `CREATE EXTENSION IF NOT EXISTS x;` — **pg_stat_statements** (top queries by total/mean time — first stop for slow-query hunting), `pg_trgm`, `pgcrypto`, `postgis`, `pg_partman`.
- Key GUCs: `shared_buffers` ~25% RAM, `effective_cache_size` ~50-75% RAM (planner hint), `work_mem` (per sort/hash node — multiply by concurrency!), `maintenance_work_mem`, `random_page_cost` ~1.1 on SSD, `max_wal_size`. Reload: `SELECT pg_reload_conf();`.

## VACUUM / bloat
- UPDATE/DELETE leave dead tuples; **autovacuum** reclaims space + refreshes planner stats + prevents **transaction-ID wraparound** (freezing). `VACUUM (VERBOSE, ANALYZE) t;`. `VACUUM FULL` fully compacts but takes `ACCESS EXCLUSIVE` (locks table, rewrites) — prefer `pg_repack` online.
- **Long-open / `idle in transaction` txns hold the xmin horizon -> autovacuum can't remove dead tuples -> bloat + plan degradation.** Find: `pg_stat_activity WHERE state='idle in transaction'`; set `idle_in_transaction_session_timeout`; always commit/rollback.
- Monitor: `pg_stat_user_tables` (`n_dead_tup`, `last_autovacuum`), `age(datfrozenxid)` for wraparound risk.

## psql
- `\l` DBs · `\dt` tables · `\d tbl` describe · `\di` indexes · `\df` funcs · `\dn` schemas · `\du` roles · `\dt+` sizes.
- `\timing on` · `\x` expanded · `\e` edit · `\i file.sql` · `\copy` client-side COPY · `\conninfo` · `\watch 1`.

## Gotchas -> Fix
- **Missing index / seq scan on big table**: check `EXPLAIN ANALYZE`; add matching index; avoid functions/casts on indexed column (non-sargable) or add an expression index.
- **Bloat + slow queries**: long/idle-in-txn transactions -> close them, set `idle_in_transaction_session_timeout`; `pg_repack`.
- **Connection exhaustion**: too many app connections -> PgBouncer (transaction mode) + smaller app pool; cap `max_connections`.
- **Lock contention / DDL hangs**: strong-lock migration behind long query blocks everything -> `lock_timeout` before DDL, `CREATE INDEX CONCURRENTLY`, `ADD COLUMN` without volatile default (PG11+ is fast).
- **Serialization/deadlock errors (`40001`/`40P01`)**: expected under Serializable/contention -> retry loop; consistent lock ordering.
- **`timestamp` TZ bugs**: use `timestamptz`. **Float money**: use `numeric`.
- **`work_mem` OOM**: it's per node per connection; a big query × many conns blows RAM -> tune conservatively, raise per-session for batch jobs.
- **Stale stats -> bad plans**: `ANALYZE`; raise `default_statistics_target` for skewed columns.
- **Sequence gaps**: expected; don't use IDs as a count.
