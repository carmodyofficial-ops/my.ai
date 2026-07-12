# Analytics Databases (OLAP)

Column-oriented engines for **aggregations/scans over billions of rows** (dashboards, reporting, event analytics). Trade point-lookup/mutation speed for scan/aggregate throughput.

## OLAP vs OLTP
- **OLTP** (Postgres, MySQL): many small transactions, point reads/writes by key, row storage, normalized, ACID, low latency per row. Query touches few rows, many columns.
- **OLAP** (ClickHouse, DuckDB, BigQuery, Snowflake, Druid): few big analytical queries, scan/aggregate/group-by over huge row counts, **columnar**, denormalized, append-heavy, high throughput. Query touches many rows, **few columns**.
- Mismatch symptom: doing per-row `UPDATE`/`SELECT ... WHERE id=` on an OLAP engine, or `GROUP BY` over 1B rows on OLTP.

## Columnar storage — why fast for analytics
- Values of one column stored **contiguously** → read only the columns a query needs (projection pushdown); skip the rest entirely.
- **Compression** far better: homogeneous data per column → dictionary, RLE, delta, delta-of-delta, Gorilla/XOR floats, FOR. 10–100x smaller → less I/O = faster scans.
- **Vectorized execution**: process column values in batches (SIMD), tight loops, no per-row interpretation overhead. Late materialization.
- **Data skipping**: min/max/zone maps, sparse indexes, bloom filters per block → prune blocks without reading.
- Row storage wins only when you need whole rows by key (OLTP), or write single rows constantly.

## ClickHouse
- **MergeTree** family = core engine. Data stored in **parts** (immutable sorted files), background-merged. 
```sql
CREATE TABLE events (
  ts DateTime, user_id UInt64, event String, amount Float64
) ENGINE = MergeTree
ORDER BY (event, ts)          -- sorting/primary key: what you filter+group on
PARTITION BY toYYYYMM(ts);    -- coarse; enables partition pruning + cheap drops
```
- **ORDER BY = the primary key**: a **sparse** index (one mark per ~8192 rows); put low→high cardinality, most-filtered columns first. Determines data locality & skip efficiency. No separate PK needed.
- **PARTITION BY**: coarse chunks for pruning + `DROP PARTITION` (cheap retention). Keep partitions **large/few** (monthly), not per-day-per-tenant.
- **Engines**: `ReplacingMergeTree` (dedup on merge by sort key + version — eventual), `SummingMergeTree`/`AggregatingMergeTree` (pre-aggregate on merge), `CollapsingMergeTree` (sign-based upsert/delete).
- **Materialized views**: insert-time triggers that write to a target table → incremental rollups (`AggregatingMergeTree` + `-State`/`-Merge` combinators). Not lazy; compute on insert.
- **Sharding** (horizontal, `Distributed` table over shards) + **replication** (`ReplicatedMergeTree` via Keeper/ZooKeeper). Mutations (`ALTER UPDATE/DELETE`) are async, heavy, rewrite parts — avoid for row-level edits.
- `LowCardinality(String)` dictionary-encodes low-distinct columns; `PREWHERE` filters before reading other columns.

## DuckDB
- **Embedded, in-process** OLAP ("SQLite for analytics") — no server; runs in the app/notebook. Vectorized, columnar, single-file or in-memory.
- Query **Parquet/CSV/Arrow directly** without loading: `SELECT * FROM 'data/*.parquet' WHERE ...` (pushdown into Parquet row groups). Zero-copy with pandas/Polars/Arrow.
- Great for: local/ad-hoc analytics, ETL transforms, testing, single-node <~TB, embedding analytics in an app. Not for concurrent multi-writer OLTP or huge cluster scale.

## Schema design for analytics
- **Star schema**: central **fact** table (events/measures, one row per event, FKs) + **dimension** tables (descriptive attributes: user, product, date). Snowflake schema = normalized dims (usually avoid; denormalize for scan speed).
- **Denormalize**: pre-join dims into the fact / wide tables to avoid runtime joins (joins are the expensive op in OLAP). Trade storage + duplication for query speed.
- **Pre-aggregate** common rollups (materialized views, summary tables) rather than scanning raw each query.
- Grain: define fact grain (one row per what) explicitly; keep additive measures additive.

## When which
- **Postgres/OLTP**: transactional app, <~100M rows analytics, need updates + joins + ACID. Add columnar ext (cstore/Hydra/Citus) before jumping.
- **ClickHouse/Druid/Pinot**: real-time high-ingest event analytics, sub-second dashboards, self-hosted, huge cardinality.
- **DuckDB**: single-node/embedded/local, Parquet lakes, notebooks, ETL.
- **Cloud warehouse (Snowflake/BigQuery/Redshift)**: elastic separated storage/compute, SQL analytics, governance, multi-team, don't want to run infra. "Warehouse" = managed OLAP at scale; analytics DB = often self-managed/real-time/embedded.

## Aggregation performance levers
- **Prune first**: partition pruning + primary-key skip index + `PREWHERE` cut blocks before scan. Verify `EXPLAIN indexes=1` shows granules skipped.
- **Approximate aggregates** for cardinality/quantiles at scale: `uniqCombined`/`uniqHLL12` (HLL), `quantileTDigest`, `topK` — orders of magnitude cheaper than exact `uniqExact`/`quantileExact`.
- **Pre-aggregate** with `AggregatingMergeTree` + materialized view storing partial states (`-State`), query with `-Merge`; dashboards read the rollup, not raw.
- **Dictionaries** (`dictGet`) for star-schema dimension lookups instead of joins.
- Vectorized engines love **wide scans of few columns** — narrow projections + columnar codecs (ZSTD/Delta) minimize I/O.

## Consistency & mutability model
- OLAP engines are typically **append-optimized, eventually-consistent on merges**, weak/no per-row transactions. Updates/deletes are batch/async part-rewrites, not OLTP semantics.
- Dedup/upsert patterns: `ReplacingMergeTree` (merge-time, eventual — query with `argMax(col, version)` for immediate correctness), `CollapsingMergeTree` (sign +1/−1 rows). Deletes best done by `DROP PARTITION`.
- No FK enforcement, limited/late constraints — quality must be enforced upstream.

## Gotchas -> Fix
- **Row-by-row / single-row INSERTs** into ClickHouse → one tiny part per insert → "too many parts" error, merge storm. Fix: **batch** (10k–1M rows/insert), buffer client-side, `async_insert`, or use `Buffer`/Kafka engine.
- **Too many small parts / over-partitioning** (`PARTITION BY` day+tenant) → merge pressure, slow. Fix: coarse partitions (month), fewer/larger; don't partition by high-cardinality.
- **Wrong `ORDER BY`/sort key** (or high-cardinality column first, or matching nothing you filter on) → no skipping, full scans. Fix: order by most-filtered, low→high cardinality; test with `EXPLAIN`.
- **Treating OLAP as mutable** — frequent `UPDATE`/`DELETE`/upsert of individual rows → part rewrites, async lag, stale reads. Fix: append-only + `ReplacingMergeTree`/`FINAL`/versioning; batch deletes by partition drop.
- **High-cardinality `GROUP BY`/`DISTINCT`** (uuid, user_id) → memory blowup, spill. Fix: approximate (`uniqCombined`/HLL, `quantileTDigest`), pre-aggregate, `LowCardinality` where distinct is bounded.
- **Runtime joins of two huge tables** → slow/OOM. Fix: denormalize/pre-join into fact, dictionary lookups (`dictGet`), or ensure join key co-located/small side.
- **`SELECT *`** on wide columnar tables defeats projection pushdown. Fix: select only needed columns.
- **Reading Parquet without pushdown** (row-group filters not applied). Fix: filter on partitioned/sorted columns, keep row groups reasonably sized, prune files by path.
- **Using a warehouse for OLTP** (point lookups, per-row writes, transactions) → costly, slow, concurrency limits. Fix: keep transactional workload in Postgres; sync to OLAP via CDC/ETL.
- **`FINAL` on every query** (to force ReplacingMergeTree dedup) → slow. Fix: dedup at query with `argMax`/aggregation, or accept eventual merge; use `FINAL` sparingly.
- **No compression codec tuning** → default. Fix: pick codecs (`Delta`, `DoubleDelta`, `Gorilla`, `ZSTD`) per column type.
- **Small-file problem** in data lakes (many tiny Parquet) → planning overhead. Fix: compaction into larger files.
```
