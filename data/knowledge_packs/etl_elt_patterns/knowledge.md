# ETL / ELT Patterns

## ETL vs ELT
- **ETL**: Extract → Transform (in a separate engine, e.g. Spark) → Load into warehouse. Transform before landing. Use when: heavy transforms unsuited to SQL, PII must be masked before landing, target compute is limited/expensive.
- **ELT**: Extract → Load raw → Transform **in-warehouse** (dbt/SQL). Land raw first, transform with warehouse compute. Modern default with cloud warehouses (Snowflake/BigQuery) — cheap storage, elastic compute, raw preserved for reprocessing, transforms versioned in SQL.
- ELT keeps an immutable raw copy → reprocess without re-extracting from source.

## Extraction
- **Full extract**: pull entire source each run. Simple, idempotent, but expensive/slow at scale. OK for small dims.
- **Incremental extract**: pull only changed rows since last run.
  - **Watermark/high-water-mark**: track `max(updated_at)`; next run `WHERE updated_at > last_watermark`. Requires a reliable, monotonic modified column. Use `>=` with dedupe, or overlap window, to avoid boundary misses.
  - **CDC (Change Data Capture)**: read the DB transaction log (Debezium/binlog/WAL) → capture inserts/updates/**deletes** as a stream. Low source load, catches deletes (watermarks can't), near-real-time. Emits before/after images + op type.
- Watermark misses **hard deletes** and rows updated without touching the timestamp — CDC handles both.

## Idempotent Loads
- Re-running a load must not create duplicates or drift. Techniques:
  - **Partition overwrite**: delete + rewrite the target partition for the run's date. Deterministic per window.
  - **MERGE / upsert**: `MERGE INTO tgt USING src ON tgt.key=src.key WHEN MATCHED UPDATE WHEN NOT MATCHED INSERT`. Key on business/primary key.
  - **INSERT OVERWRITE** by partition (Spark/Hive).
- Avoid blind `INSERT ... SELECT` appends — retries duplicate rows.

## Deduplication
- Sources deliver dupes (retries, at-least-once, CDC replays). Dedupe by PK keeping latest:
```sql
row_number() over (partition by pk order by updated_at desc) = 1
```
- Dedupe on a stable **event/business key**, not on ingestion metadata.

## Late-Arriving Data
- **Late facts**: events arrive after their window closed → reprocess affected partitions (idempotent overwrite makes this safe), or use streaming **watermark + allowed lateness**.
- **Late-arriving (early-arriving) dimensions**: fact references a dim key not yet present → insert an **inferred/unknown member** placeholder (surrogate `-1` or stub row), backfill attributes when the dim lands.

## Slowly Changing Dimensions in Loads
- **SCD1**: MERGE overwrite current value.
- **SCD2**: on change, close current row (`valid_to=now, is_current=false`) and insert a new versioned row (new surrogate key). Detect change via hash of tracked columns; unchanged → no-op.

## Data Validation + Quarantine
- Validate on load: schema/type, not-null PKs, uniqueness, ranges, referential integrity, row-count vs source.
- **Quarantine** invalid rows to a reject/error table with reason + keep the good rows flowing; alert + reconcile. Don't fail the whole batch for a few bad rows (unless contract requires).
- Enforce a **schema contract** at ingest; reject/route on violation.

## Orchestration + Retries + Backfill
- Orchestrator (Airflow/Dagster) parameterizes each run by **logical/interval date**; tasks idempotent → safe retries + backfills.
- Backfill = replay the same idempotent load over historical windows. Never depend on `now()`; derive windows from the run interval.
- Retries with idempotent loads are safe; non-idempotent loads corrupt on retry.

## Batch vs Micro-batch vs Streaming
- **Batch**: scheduled windows, high throughput, simple reprocessing, minutes–hours latency. Default.
- **Micro-batch**: small frequent batches (seconds–minutes) — near-real-time with batch simplicity (Spark Structured Streaming, small dbt runs).
- **Streaming**: per-event, sub-second, stateful, hardest (ordering, exactly-once, late data). Use only for genuine low-latency SLAs.

## Reprocessing Strategies
- Keep **raw immutable** (bronze) → recompute derived layers anytime.
- **Idempotent, partition-scoped** transforms → reprocess a date range by re-running those partitions.
- **Blue/green (swap) tables**: build into a new table, validate, atomically swap → no partial-state exposure.
- Version transformation logic (dbt/git) so a reprocess reproduces exactly.

## Reconciliation
- After each load, compare **source vs target** counts/checksums/sums by partition; alert on drift. Catches silent loss/dupe that row-level checks miss.

## CDC Mechanics
- **Log-based** (Debezium on MySQL binlog / Postgres WAL / Oracle redo): lowest source impact, captures every change incl. deletes, ordered by LSN. Preferred.
- **Query-based** (poll `WHERE updated_at > watermark`): simple, no special source access, but misses deletes + intermediate updates, adds source query load.
- **Trigger-based**: DB triggers write a changelog table — captures deletes but adds write overhead on source.
- CDC event = op type (`c/u/d/r`), before + after images, source metadata (LSN, ts). Apply to target via MERGE keyed on PK ordered by LSN.
- **Snapshot + stream**: initial full snapshot, then switch to log tailing for ongoing changes (Debezium does this automatically).

## Merge / Upsert Patterns
```sql
MERGE INTO tgt t USING stg s ON t.id = s.id
WHEN MATCHED AND s.op='d' THEN DELETE
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...
```
- Dedupe the staging/source **before** MERGE (one row per key) — MERGE errors or is nondeterministic on duplicate source keys.
- For append-only warehouses (BigQuery/Snowflake), `MERGE` or `INSERT OVERWRITE` partition; delete+insert within a transaction for atomicity.

## Watermark Bookkeeping
- Persist last-processed watermark (max updated_at / LSN / file timestamp) in a control table or orchestrator variable — commit only after successful load (atomic with the load if possible).
- Use a **lookback/overlap window** (`> watermark - Δ`) + idempotent MERGE to catch late/boundary updates safely.
- Never advance the watermark on a partial/failed load.

## Staging + Zones
- **Landing/raw zone**: exact source copy, immutable, append-only (bronze). Enables replay without re-extracting.
- **Staging**: typed, deduped, conformed working area (silver).
- **Serving/marts**: modeled facts/dims + aggregates (gold).
- Load raw → transform in place; each zone re-derivable from the prior.

## Reconciliation Patterns
- **Row-count** parity source vs target per partition/day.
- **Control totals / checksums**: sum of a numeric column, hash of PK set.
- **Freshness**: max event/load timestamp vs SLA.
- Store per-run stats (rows read/written/rejected) and alert on drift or unexpected zero-row loads.

## Gotchas -> Fix
- **Non-idempotent load** (append) → dupes on retry/backfill → partition-overwrite or MERGE on key.
- **Silent data loss** (watermark boundary skip / dropped bad rows) → overlap window + `>=` + dedupe; quarantine not discard; **reconcile counts**.
- **No reconciliation** → drift undetected for weeks → add source/target count+sum checks per load.
- **Watermark misses deletes** → target keeps ghost rows → use CDC, or periodic full-reconcile/soft-delete flags.
- **Timestamp-based incremental with clock skew / non-monotonic updated_at** → missed rows → CDC or use DB-server time + lookback window.
- **CDC replay duplicates** (at-least-once) → dedupe by key + op sequence/LSN, keep latest.
- **Late data dropped by fixed window** → allowed-lateness/watermark, or idempotent partition reprocess.
- **Early-arriving fact, missing dim** → NULL/failed FK → inferred member placeholder, backfill later.
- **Full refresh masquerading as incremental** (rebuilds everything) → true incremental with `unique_key` + watermark.
- **Transform reads mutable raw** (source changed under you) → land immutable raw snapshot; transform from it.
- **Dedupe on ingestion timestamp** instead of business key → keeps wrong/dup versions → dedupe on stable key ordered by source updated_at.
- **Backfill uses `now()`** → wrong windows → parameterize by logical/interval date only.
- **MERGE on duplicate source keys** → nondeterministic/failed merge → dedupe staging to one row per key first.
- **Watermark advanced on partial failure** → permanent gap → commit watermark only on full success.
- **Schema drift breaks load silently** (extra/missing columns) → enforce contract, `on_schema_change` handling, alert.
- **Timezone mismatch** between source and watermark → missed/duplicated windows → normalize all to UTC.
- **Deletes never propagate** (append-only ELT) → stale rows linger → CDC delete events or periodic full reconcile with soft-delete flags.

## When to Use Which
- **Full extract + overwrite**: small tables, no reliable change column. Simple + idempotent.
- **Watermark incremental**: large tables with a trustworthy monotonic `updated_at`, deletes rare/irrelevant.
- **CDC**: high-volume, need deletes + near-real-time + low source impact.
- **Streaming**: genuine sub-minute SLA; else micro-batch or batch.
- **ELT**: cloud warehouse target, SQL transforms, want raw preserved. **ETL**: pre-load masking, non-SQL transforms, constrained target.
