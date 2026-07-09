# Data Engineering Fundamentals

## Batch vs Streaming
- **Batch**: bounded data, processed in scheduled windows (hourly/daily). High throughput, high latency (minutes–hours). Simpler, cheaper, easy reprocessing. Tools: Spark, dbt, Airflow.
- **Streaming**: unbounded data, processed per-event or micro-batch. Low latency (ms–s), harder state/ordering/exactly-once. Tools: Kafka, Flink, Spark Structured Streaming.
- **Micro-batch**: streaming emulated via tiny batches (Spark ~seconds). Middle ground.
- Choose batch unless you have a real latency SLA. Most "real-time" needs are satisfied by 5-min micro-batch.
- **Lambda architecture**: batch layer + speed layer merged at serving. **Kappa**: single streaming path, reprocess by replaying log. Kappa preferred now (one codebase).

## Pipeline Architecture
- Stages: **ingest → store (raw) → transform → serve**. Land raw immutable first, transform later (ELT).
- **Medallion**: bronze (raw), silver (cleaned/conformed), gold (aggregated/business). Each layer re-derivable from prior.
- Decouple stages via storage/queues so failures are isolated and retryable.
- Orchestrator (Airflow/Dagster) owns dependencies, scheduling, retries, backfills — not the compute engine.

## Storage Formats
- **Parquet**: columnar, compressed, splittable. Default for analytics. Predicate/column pushdown; only reads needed columns. Row groups (~128MB) + column stats (min/max) enable skipping.
- **ORC**: columnar like Parquet, strong in Hive/Trino, built-in indexes + bloom filters.
- **Avro**: row-based, compact binary, embeds schema, great for streaming/Kafka and record-by-record writes; strong schema evolution.
- **CSV/JSON**: row, text, not splittable well (JSON), no types, no pushdown — avoid at scale except interchange.
- **Columnar wins** for analytical scans (few cols, many rows); **row** wins for whole-record writes/reads (OLTP, streaming).
- Compression: **Snappy** (fast, splittable, default), **Zstd** (better ratio, tunable), **Gzip** (high ratio, NOT splittable → avoid for large files), **LZ4** (fastest).

## Partitioning + File Sizing
- Partition by a **low-cardinality, high-selectivity** column used in filters (usually date: `dt=2026-07-08`). Enables partition pruning.
- Don't over-partition: `partitionBy(date, hour, country, user_id)` explodes into tiny files.
- **Target file size 128MB–1GB.** Too small = metadata/scheduler overhead; too large = poor parallelism, memory pressure.
- Compact small files periodically (`OPTIMIZE`, coalesce, rewrite). Control output files with `repartition()`/`coalesce()` before write.
- Rule of thumb: partition count ≈ data_size / target_file_size.

## Lake vs Warehouse vs Lakehouse
- **Data lake**: cheap object storage (S3/GCS/ADLS), any format, schema-on-read, flexible, no ACID/governance by default → risk of "data swamp."
- **Warehouse**: managed columnar store (Snowflake/BigQuery/Redshift), schema-on-write, SQL, ACID, fast BI. Costlier per TB, structured only.
- **Lakehouse**: table formats (Delta/Iceberg/Hudi) add ACID transactions, schema enforcement, time travel, upserts/MERGE on top of a lake. One copy serves BI + ML.
- Table formats provide transaction log, snapshot isolation, `MERGE`, schema evolution, and compaction over Parquet files.

## Idempotency + Backfills
- **Idempotent**: re-running produces the same result (no dupes). Essential — retries and backfills WILL re-run tasks.
- Techniques: **overwrite a partition** (delete-then-write by date), **MERGE/upsert** on a key, dedupe by primary key + watermark, deterministic output paths keyed by logical date.
- Avoid append-without-dedupe and `INSERT` side effects that accumulate on retry.
- **Backfill**: reprocess historical windows. Design pipelines parameterized by `logical_date` so any window is reproducible. Backfill = loop the same idempotent task over past partitions.

## Schema Evolution
- Add columns (nullable/defaulted) = safe. Removing/renaming/retyping = breaking.
- Parquet/Avro support evolution; enforce with a **schema registry** (Kafka) or table format schema enforcement.
- **Backward compatible**: new reader reads old data. **Forward**: old reader reads new data. **Full**: both. Prefer additive changes.

## Data Quality + Validation
- Checks: not-null, uniqueness (PK), referential integrity, ranges/domains, row-count deltas, freshness/SLA, distribution drift.
- Tools: dbt tests, Great Expectations, Soda, Deequ.
- **Quarantine** bad rows to a side table rather than failing the whole load; alert + reconcile.
- Validate at ingest (contract) and post-transform (business rules).

## Lineage + Metadata
- **Lineage**: column/table-level dependency graph — impact analysis, debugging, compliance. Tools: OpenLineage, dbt docs, DataHub, Unity Catalog.
- Catalog holds schema, ownership, freshness, descriptions, PII tags.

## Cost + Scaling
- Storage cheap; **compute + shuffle + scan** expensive. Reduce scanned bytes: partitioning, columnar, pushdown, `SELECT` only needed columns.
- Separate storage/compute (Snowflake/BigQuery) → scale independently, pay per query.
- Prefer incremental over full refresh. Cache/materialize hot aggregates.
- **Vertical** (bigger box) vs **horizontal** (more nodes) scaling — distributed engines (Spark) scale horizontally; single-node tools (pandas/DuckDB) scale vertically. Right-size: don't spin a 100-node cluster for 10GB (DuckDB/pandas fine).
- Spot/preemptible instances for fault-tolerant batch → big savings. Auto-suspend idle warehouses.

## Table Formats (Delta / Iceberg / Hudi)
- All add ACID + metadata layer over Parquet files in object storage; enable the lakehouse.
- **Delta Lake**: transaction log (`_delta_log` JSON + checkpoints), `MERGE`, time travel (`VERSION AS OF`), `OPTIMIZE` (compaction) + `ZORDER` (multi-dim clustering), schema enforcement/evolution. Tight with Spark/Databricks.
- **Apache Iceberg**: hidden partitioning (partition transforms — no partition columns in queries), partition evolution without rewrite, snapshot isolation, engine-agnostic (Spark/Trino/Flink/Snowflake). Rich metadata (manifest lists).
- **Apache Hudi**: copy-on-write vs merge-on-read tables, record-level upserts/deletes, built-in incremental pulls, good for CDC ingestion.
- All support **time travel** (query historical snapshot) and **compaction** to fix small files.

## Ingestion Patterns
- **Push** (source sends: webhooks, Kafka producers) vs **pull** (you poll: API, DB query).
- **Full snapshot** vs **incremental** (watermark/CDC) vs **event stream**.
- Land raw first (immutable), decouple ingest from transform via a queue or raw zone.
- Rate limits/pagination/retry with backoff for API sources; checkpoint progress to resume.

## Processing Semantics
- **At-least-once** (dupes possible → need idempotent sinks) vs **exactly-once** (harder, needs transactional sink + dedupe) vs **at-most-once** (may lose).
- **Event time** (when it happened) vs **processing time** (when observed) — analytics should key on event time; late/out-of-order events need watermarks.
- **Watermark**: threshold declaring "no events older than X expected" → bounds state, closes windows, drops stragglers.

## Observability + SLAs
- Monitor: **freshness** (data age vs SLA), volume (row-count anomalies), schema changes, distribution drift, pipeline latency/failures.
- **Data SLA/SLO**: e.g. "gold table ready by 06:00, < 0.1% null keys." Alert on breach.
- Emit run metadata (rows in/out, duration, watermark) per run for debugging + reconciliation.

## Gotchas -> Fix
- **Small-files problem** (millions of tiny files) → slow listing/planning → compact via `OPTIMIZE`/coalesce; don't over-partition; target 128MB–1GB.
- **Data skew** (one key/partition huge) → straggler tasks/OOM → salt keys, repartition, use AQE skew join.
- **Non-idempotent loads** (append duplicates on retry) → use partition-overwrite or MERGE keyed by PK.
- **Schema drift breaks downstream** → schema registry + enforcement + additive-only changes; contract tests.
- **Full refresh of huge tables daily** → costly/slow → incremental models with watermark/CDC.
- **Timezone/date confusion in partitions** → standardize on UTC; partition on event-time not processing-time when doing event analytics.
- **Late-arriving data** silently dropped by windowing → allowed-lateness/watermark + reprocess affected partitions.
- **Schema-on-read swamp** (lake with no catalog) → govern with table format + catalog + ownership.
- **Reading gzip'd large CSV** not splittable → single-core bottleneck → convert to Parquet+Snappy.
- **No reconciliation** (source vs sink counts never checked) → silent loss → add row-count/checksum reconciliation per load.
- **Wildcard SELECT * in wide columnar tables** kills pushdown benefit → project only needed columns.
- **Processing-time partitioning for event analytics** → events land in wrong day → partition/window on event time with watermark.
- **Mutable "raw" source** (transform reads a table that keeps changing) → non-reproducible → snapshot raw immutably, transform from the snapshot.
- **No data contract** between producer/consumer → surprise breaks → version schemas, enforce compatibility, alert on drift.

## Data Modeling Basics
- **OLTP** (normalized, row store, many small txns) vs **OLAP** (denormalized/star, columnar, big scans). Warehouses are OLAP.
- Model for query patterns: pre-join/pre-aggregate what BI reads often (gold marts).
- Keep a **single source of truth** per entity; derive everything else.

## Pipeline Reliability
- **Retries with backoff** + **idempotent tasks** = safe automatic recovery.
- **Circuit breaker / dead-letter** for bad records so one poison row doesn't halt the batch.
- **Checkpointing** streaming/long jobs to resume, not restart.
- Alert on freshness/volume/failure; keep run metadata for reconciliation + debugging.
