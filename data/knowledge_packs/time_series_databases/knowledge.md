# Time-Series Databases (TSDB)

Optimized for timestamped data: high-volume append writes, time-range queries, downsampling. Metrics, IoT, monitoring, finance, events.

## Data characteristics
- Append-mostly, **rarely updated/deleted**; time-ordered; queried by time range + tags/labels.
- Each point: **timestamp + measurement/metric + tags (indexed dimensions) + fields (values)**.
- Recent data hot, old data cold → tiered retention + downsampling. Naturally compressible (delta-of-delta timestamps, XOR floats — Gorilla/Facebook).
- **Cardinality** = number of unique series = product of distinct tag-value combinations. The dominant scaling factor.

## Options
- **InfluxDB**: purpose-built; line protocol `measurement,tag=v field=v ts`; Flux/InfluxQL; tag=indexed, field=not; retention policies + continuous queries (v1) / tasks (v2) / v3 columnar (Arrow/Parquet).
- **TimescaleDB**: Postgres extension → full SQL, joins, relational + time-series. **Hypertables** auto-partition by time (+ optional space) into chunks; **continuous aggregates** (incremental materialized rollups); native columnar compression; retention/data-tiering policies.
- **Prometheus**: pull-based metrics + monitoring; local TSDB; **PromQL**; labels; 15d default retention → remote-write (Thanos/Cortex/Mimir/VictoriaMetrics) for long-term + scale. Alerting.
- Others: VictoriaMetrics (Prom-compatible, efficient), Graphite, QuestDB, ClickHouse (analytics), AWS Timestream.

## Downsampling, retention, rollups
- **Downsample**: store raw at high res short-term; roll up to 1m/1h/1d aggregates for long-term (avg/min/max/sum/count/percentiles). Keep enough resolution per age tier.
- **Retention policy**: auto-drop/expire raw data after N days (drops whole chunks/shards — cheap). Keep rollups longer.
- **TimescaleDB continuous aggregate**: `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` + `time_bucket('1 hour', ts)`; refreshed incrementally by policy → fast dashboards.
- **Prometheus recording rules** precompute expensive PromQL; downsampling via Thanos/Mimir.

## Hypertables & continuous aggregates (TimescaleDB)
```sql
SELECT create_hypertable('metrics','ts', chunk_time_interval => INTERVAL '1 day');
SELECT time_bucket('5 minutes', ts) AS b, device_id, avg(temp)
FROM metrics GROUP BY b, device_id ORDER BY b;
ALTER TABLE metrics SET (timescaledb.compress, timescaledb.compress_segmentby='device_id');
SELECT add_retention_policy('metrics', INTERVAL '90 days');
```
- Chunk interval: aim ~25% RAM per chunk; too small = overhead, too big = poor compression/eviction.

## Cardinality & tag/label design
- Series count = ∏ (unique values per tag). Adding a high-cardinality tag multiplies series → memory/index blowup ("cardinality explosion").
- **Keep as tags**: bounded, low-cardinality, queried/grouped dimensions (region, host, status). **Keep as fields/values**: unbounded/high-cardinality (user_id, request_id, raw value, email, UUID, latency).
- Budget total series; monitor cardinality (`SHOW SERIES CARDINALITY`, Prometheus `count({__name__=~".+"})`).

## Ingestion & querying
- Batch writes (line protocol / remote-write), out-of-order handling windows, backfill considerations.
- Query building blocks: **time windows / bucketing** (`time_bucket`, `GROUP BY time()`), **aggregation** (avg/percentile), **gap-filling / interpolation** (`time_bucket_gapfill`, `fill()`, `LOCF`), **rate/delta/increment** for counters (`rate()`, `increment()`, `derivative`), **moving averages**, **downsample on read**.
- Counters reset on restart → always use `rate()`/`irate()`, never raw diff.

## Compression & storage internals
- Timestamps: **delta-of-delta** encoding (regular intervals → near-zero bytes). Float values: **XOR/Gorilla** encoding. Tags: dictionary/columnar.
- Typical 10-20x compression on real metrics. Columnar layout (Timescale compressed chunks, Influx v3 Parquet) → fast scans/aggregation, but compressed data is slower to update.
- Tiered storage: hot (uncompressed, recent) → warm (compressed) → cold (object storage / S3-tiered).

## Prometheus specifics
- **Pull** model: scrapes `/metrics` targets on interval; service discovery. Metric types: counter, gauge, histogram, summary.
- PromQL: `rate(http_requests_total[5m])`, `histogram_quantile(0.99, ...)`, `sum by (job) (...)`, `increase()`, `avg_over_time`.
- Labels are the dimensions (= series cardinality driver). Alertmanager for routing/dedup/silencing. `remote_write` to long-term stores.

## Ingestion patterns
- **Batch + async**: buffer points client-side, flush in batches (line protocol / remote-write) — never one HTTP call per point.
- **Push** (Influx, Timescale inserts, Prometheus Pushgateway for batch jobs) vs **pull** (Prometheus scrape).
- Handle **out-of-order** + **late/backfill** data within a configured window; dedup by (series, timestamp) — same key overwrites.
- Precision: pick timestamp precision (s/ms/ns) deliberately; excessive precision wastes space.

## Query building blocks (detail)
- **Windowing**: `time_bucket('1m', ts)` / `GROUP BY time(1m)` — align to buckets. **Aggregation**: avg/min/max/sum/count/percentile per bucket.
- **Gap-fill**: `time_bucket_gapfill` + `LOCF`/interpolate / Influx `fill(previous|linear|none|0)`.
- **Rate/derivative**: `rate()`/`irate()`/`increase()` for counters; `derivative`/`delta` for gauges; **moving average**/EMA for smoothing.
- **Downsample-on-read** for wide ranges; select from continuous aggregate/rollup instead of raw.

## Gotchas -> Fix
- **High cardinality explosion** (unbounded tag: user_id, uuid, url with ids, ip) → OOM, slow, index bloat. Fix: move high-cardinality dims to fields/values not tags; drop/aggregate labels; cardinality budget + monitoring; relabel/drop rules.
- **Unbounded labels** from dynamic values (error messages, paths) → new series per value. Fix: normalize/templatize labels (`/user/:id`), bucket, allowlist label values.
- **Retention misconfig** (too long → disk full; too short → data lost) . Fix: explicit retention per tier; downsample before dropping raw; alert on disk.
- **Wrong tag vs field choice** → either unqueryable (needed dim as field) or cardinality blowup (unbounded as tag). Fix: tags for bounded queried dims only.
- **Raw counter subtraction** ignores resets → negative/garbage rates. Fix: `rate()`/`increment()` counter functions.
- **Querying huge raw range** on dashboards → slow/timeouts. Fix: query continuous aggregates/rollups; downsample-on-read; limit range.
- **No downsampling** → raw high-res kept forever, storage explodes. Fix: rollups + retention policy per age.
- **Out-of-order / late writes** rejected or mis-bucketed. Fix: configure OOO window; backfill into correct chunks; idempotent writes.
- **Bad chunk interval** (too many tiny chunks or giant chunks) → planning overhead / poor compression. Fix: size chunks ~ fit RAM; tune `chunk_time_interval`.
- **Using generic RDBMS for TS at scale** → bloated indexes, slow range scans, vacuum pain. Fix: hypertables/TSDB with time partitioning + compression.
- **Missing gap-fill** → dashboards show holes/misleading lines. Fix: `time_bucket_gapfill`/`fill(previous/linear)`.
- **Prometheus as long-term/high-cardinality store** → local retention + memory limits. Fix: remote-write to Thanos/Mimir/VictoriaMetrics; keep label cardinality low.
- **Updating compressed/old chunks** is slow/unsupported. Fix: append-only design; decompress-modify-recompress only for rare backfill.
- **Timestamp precision too high** (ns everywhere) wastes space + index. Fix: match precision to real sampling rate.
- **Regex/`ALLOW FILTERING`-style scans over all series** on dashboards → timeouts. Fix: pre-aggregate, constrain by tag + time, recording rules.
- **Duplicate points** from retries at same (series, ts) silently overwrite or double-count depending on engine. Fix: idempotent writes keyed by series+ts; understand engine's dedup semantics.

## Choosing a TSDB
- Need full SQL, joins with relational data, complex queries → **TimescaleDB** (Postgres).
- Pure metrics + alerting + Kubernetes/exporters ecosystem → **Prometheus** (+ long-term backend).
- High-throughput IoT ingest, purpose-built, tag/field model → **InfluxDB**.
- Prometheus-compatible but far more efficient/scalable → **VictoriaMetrics**.
- Analytical, huge scale, SQL OLAP over events → **ClickHouse/QuestDB**.

## Capacity & operational sizing
- Estimate: series_count x sample_rate x retention x bytes/point (post-compression ~1-2 bytes). Cardinality dominates memory.
- Keep active series within engine limits (Prometheus head ~ RAM-bound; Influx TSI index). Alert on series growth.
- Shard by tenant/metric; replicate for HA; separate ingest from query workloads at scale.
