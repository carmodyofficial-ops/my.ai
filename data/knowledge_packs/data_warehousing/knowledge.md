# Data Warehousing

## Dimensional Modeling
- **Fact table**: measurements/events at a defined **grain**; numeric **measures** + foreign keys to dimensions. Long + narrow, high row count. Types: **transaction** (one row/event), **periodic snapshot** (one row/entity/period), **accumulating snapshot** (one row/process, updated).
- **Dimension table**: descriptive context (who/what/where/when) — wide, low row count, denormalized attributes. E.g. `dim_customer`, `dim_product`, `dim_date`.
- **Star schema**: central fact + directly-joined denormalized dimensions. Fewer joins, fast BI. Preferred.
- **Snowflake schema**: dimensions normalized into sub-dimensions. Less redundancy, more joins, slower. Avoid unless storage/consistency demands it.
- Always have a **`dim_date`** (calendar) dimension for time analysis.

## Grain
- **Grain = what one fact row represents.** Declare it FIRST, before columns. e.g. "one row per order line item."
- All measures must be true at that grain; all dimensions must apply. Mixing grains → wrong aggregations.
- Finer grain = more flexible + bigger; pre-aggregated grain = smaller + less flexible.

## SCD (Slowly Changing Dimensions)
- **Type 0**: never change (retain original).
- **Type 1**: overwrite — no history (just current value). Simple; loses past.
- **Type 2**: add a new row per change with `valid_from`/`valid_to` + `is_current` flag (and new surrogate key) → full history. Facts join to the version valid at event time. Most common for tracking history.
- **Type 3**: add a column (`prev_value`) — limited history (one prior). Rare.
- Type 2 is the default when you need "what did this attribute look like when the fact happened."

## Surrogate Keys
- System-generated integer/hash PK for each dimension row, independent of source **natural/business key**.
- Enables SCD2 (same business key, multiple surrogate keys), decouples from source, handles late/unknown members, faster joins.
- Add a **"-1 / unknown" member** for missing/late-arriving keys instead of NULL FKs.

## Normalization vs Denormalization
- **Normalized (3NF)**: no redundancy, integrity, good for OLTP writes. Many joins → poor analytics.
- **Denormalized (star)**: redundancy for read speed, fewer joins. Warehouses favor denormalization; storage is cheap, scan/join is the cost.

## Columnar Warehouses
- **Snowflake**: separate storage/compute; virtual warehouses (compute) scale independently; micro-partitions auto-managed; **clustering keys** for pruning; time travel. Pay per compute-second.
- **BigQuery**: serverless, columnar; **partitioning** (by date/ingestion/int range) + **clustering** (up to 4 cols) to prune scanned bytes; priced by **bytes scanned** (or slots).
- **Redshift**: cluster-based; **DISTKEY** (co-locate join keys across nodes), **SORTKEY** (zone-map pruning / range scans); `VACUUM`/`ANALYZE` maintenance.
- Common theme: minimize **bytes scanned** via partition/cluster/sort + column pruning.

## Incremental Models + dbt
- **dbt**: SQL-based transformation (T in ELT); compiles `SELECT`s into tables/views in the warehouse.
- **`ref()`** builds the DAG + handles dependency order; **`source()`** references raw tables.
- **Materializations**: `view` (no storage, recompute), `table` (full rebuild), **`incremental`** (append/merge only new rows), `ephemeral` (inlined CTE).
- Incremental pattern: `{% if is_incremental() %} where updated_at > (select max(updated_at) from {{ this }}) {% endif %}` + `unique_key` for merge → avoids full refresh.
- **Tests**: `unique`, `not_null`, `accepted_values`, `relationships` (FK), plus custom/singular tests. `dbt test` in CI.
- **Snapshots**: dbt's SCD2 implementation (`strategy=timestamp/check`).

## Query Optimization + Cost
- Prune scans: partition + cluster/sort on filter/join columns; `SELECT` only needed columns.
- Filter early; avoid `SELECT *` (bytes-scanned billing).
- Pre-aggregate hot metrics (gold/aggregate tables); materialize expensive joins.
- Avoid high-cardinality `GROUP BY`/`DISTINCT` on huge tables when a rollup suffices.

## Medallion (Bronze/Silver/Gold)
- **Bronze**: raw ingested, append-only, immutable, minimal transform.
- **Silver**: cleaned, deduped, conformed, typed, joined — the integrated model.
- **Gold**: business-level aggregates/marts (star schemas, metrics) for BI/ML. Each layer re-derivable from the one below.

## Additive / Semi-Additive / Non-Additive
- **Additive** measures sum across all dimensions (e.g. `sales_amount`) — safest.
- **Semi-additive** sum across some dims but not time (e.g. account balance, inventory level) — sum over products but average/last over time.
- **Non-additive** (ratios, percentages, unit price) — never sum; recompute from additive components at the query grain.
- Store additive components; derive ratios in the BI layer.

## Conformed Dimensions + Bus Matrix
- **Conformed dimension**: same dimension (same keys/attributes) shared across multiple fact tables → enables cross-process drill-across (e.g. `dim_date`, `dim_customer` used by sales + returns).
- **Bus matrix**: business processes (rows) × dimensions (columns) — the warehouse design blueprint ensuring conformance.
- **Drill-across**: query each fact separately at a common grain on conformed dims, then merge results (never join fact-to-fact directly).

## Fact Table Types + Degenerate/Factless
- **Degenerate dimension**: dimension key with no attributes stored in the fact (e.g. `order_number`) — kept in the fact row.
- **Factless fact**: rows record events/coverage with no measures (e.g. student attendance, promotion eligibility) — count rows.
- **Bridge table**: resolves many-to-many between fact and dimension (e.g. multiple diagnoses per visit) with allocation factors to avoid double counting.

## Clustering / Partitioning Detail
- **BigQuery**: partition on a single date/timestamp/int column (or ingestion time); cluster on up to 4 cols (order matters — most-filtered first). `require_partition_filter` forces pruning.
- **Snowflake**: auto micro-partitions; define **clustering keys** on large tables filtered/joined on high-cardinality cols; monitor `SYSTEM$CLUSTERING_INFORMATION`; reclustering costs credits.
- **Redshift**: `DISTSTYLE` (KEY co-locates join keys, ALL replicates small dims, EVEN default); compound vs interleaved `SORTKEY`; `ANALYZE` stats + `VACUUM` reclaim/resort.

## dbt Project Structure
- `models/` staging (`stg_`, 1:1 with source, light cleanup) → intermediate (`int_`) → marts (`fct_`/`dim_`).
- `sources.yml` (freshness + schema), `schema.yml` (tests + docs), `dbt_project.yml` (materialization config per folder).
- `{{ config(materialized='incremental', unique_key='id', on_schema_change='append_new_columns') }}`.
- `dbt run`, `dbt test`, `dbt build` (run+test in DAG order), `dbt snapshot` (SCD2). Macros + packages (`dbt_utils`) for reuse.

## Gotchas -> Fix
- **Fan-out / fact-to-fact join** (joining two facts, or a many-side dimension) multiplies rows → inflated measures → join facts only through conformed dimensions; keep one fact per query, aggregate before joining.
- **Wrong grain** (measures at mixed grains) → double counting → declare grain first; one fact per grain.
- **Full refresh of huge tables** nightly → cost/time → dbt incremental with `unique_key` + watermark.
- **SCD Type 1 where history needed** → lost past states → use Type 2 with valid_from/to.
- **NULL foreign keys** for late/missing dims → broken joins/filters → unknown member (`-1`) + surrogate keys.
- **`SELECT *` on BigQuery** → bills all columns' bytes → select explicit columns; partition filter required patterns.
- **No partition/cluster** → full-table scans every query → add partition on date + cluster/sort on filter cols.
- **Snowflaked dims** slow BI with join sprawl → denormalize into star.
- **Double-counting additive-only measures** (averaging a semi-additive/snapshot measure across time) → know additive vs semi- vs non-additive.
- **dbt incremental missing late-arriving updates** (watermark skips them) → use MERGE on `unique_key` with a lookback window.
- **Distinct counts across SCD2** without date filter → counts every version → filter `is_current` or valid range.
- **Unbounded VACUUM debt (Redshift)** → bloated sort → schedule VACUUM/ANALYZE.
- **Summing semi-additive measure over time** (balance/inventory) → wrong totals → last/avg over time, sum over other dims.
- **Summing a non-additive ratio** (avg of averages) → recompute from additive numerator/denominator at query grain.
- **Many-to-many flattened into fact** → double counting → bridge table with allocation factors.
- **Reclustering/large clustering keys** run every load → credit burn → cluster only large, frequently-filtered tables; monitor clustering depth.

## Query Cost Levers (recap)
- Partition + cluster/sort on filter/join columns; require partition filters.
- Project explicit columns (columnar + bytes-scanned billing).
- Materialize expensive joins/aggregates into gold tables; incremental refresh.
- Right-size compute (warehouse size / slots); auto-suspend idle warehouses.
- Push filters before joins; avoid `SELECT DISTINCT`/`GROUP BY` on huge high-cardinality sets when a rollup exists.
