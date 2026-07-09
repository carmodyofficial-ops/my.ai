# Apache Spark

## Architecture
- **Driver**: runs `main`, builds DAG, schedules stages/tasks, holds `SparkSession`. Single point — don't `collect()` huge data to it.
- **Executors**: JVM processes on worker nodes running tasks, holding cache blocks and shuffle data. Each has cores (task slots) + memory.
- **Cluster manager**: YARN / Kubernetes / Standalone allocates executors.
- **Job → Stages → Tasks**: an action triggers a job; shuffle boundaries split stages; a task = one partition of a stage.
- One **task per partition per core**. Parallelism = total executor cores.

## RDD vs DataFrame vs Dataset
- **RDD**: low-level, typed, no optimizer, no schema. Use only for fine-grained control/unstructured data.
- **DataFrame**: `Row`-based table with schema; goes through **Catalyst** optimizer + **Tungsten** codegen. Default for most work.
- **Dataset** (Scala/Java): typed DataFrame; compile-time safety. Not in PySpark.
- Prefer DataFrame/SQL — optimizer does predicate pushdown, column pruning, join reordering. UDFs (esp. Python) bypass optimization → avoid when a built-in exists.

## Transformations vs Actions (lazy)
- **Transformations** (`select`, `filter`, `join`, `groupBy`, `withColumn`) are **lazy** — build lineage, execute nothing.
- **Actions** (`show`, `count`, `collect`, `write`, `take`, `foreach`) trigger execution.
- **Narrow** (map/filter) = no shuffle, pipelined. **Wide** (groupBy/join/distinct/repartition) = shuffle.

## Partitioning + Shuffle
- **Shuffle** = repartition data across network by key → expensive (disk + network + serialization). Minimize.
- `spark.sql.shuffle.partitions` (default 200) sets post-shuffle partition count. Tune to data size (aim ~128MB/partition), not left at 200 for huge or tiny data.
- `repartition(n)` = full shuffle to n partitions (even). `coalesce(n)` = merge without full shuffle (use to reduce files before write).
- Enable **AQE** (`spark.sql.adaptive.enabled=true`, default in 3.x) — coalesces shuffle partitions, switches join strategy, and splits skewed partitions at runtime.

## Joins
- **Broadcast hash join**: ships small side to every executor, no shuffle of big side. Auto when one side < `spark.sql.autoBroadcastJoinThreshold` (default 10MB) or force `broadcast(df)`. Fastest — use for large⋈small (dimension) joins.
- **Sort-merge join**: default for large⋈large; shuffles both sides by key, sorts, merges.
- **Shuffle hash join**: builds hash table per partition; less common.
- Broadcasting too-large a table → driver/executor OOM. Raise threshold cautiously.

## Caching / Persist
- `cache()` = `persist(MEMORY_AND_DISK)`. Use when a DataFrame is reused across multiple actions/branches.
- Lazy — materialized on first action. `unpersist()` when done to free memory.
- Storage levels: `MEMORY_ONLY`, `MEMORY_AND_DISK` (default, spills), `DISK_ONLY`, `_SER` (serialized, less mem, more CPU).
- Don't cache a DF used once — wastes memory and can cause spills.

## Skew Handling
- Symptom: one/few tasks run far longer, others done — long tail; possible OOM on the hot task.
- **AQE skew join** (`spark.sql.adaptive.skewJoin.enabled`) auto-splits large skewed partitions.
- **Salting**: add random suffix to hot key, replicate the small side across salt values, join, then aggregate — spreads a hot key across partitions.
- Broadcast the smaller side to avoid shuffling the skewed key at all.
- Separate the skewed keys and handle them independently.

## Structured Streaming
- Treats stream as an unbounded table; same DataFrame API. Micro-batch (default) or continuous.
- `readStream`/`writeStream`; **triggers**: default (ASAP), `processingTime`, `availableNow`, `once`.
- **Output modes**: `append` (new rows), `update` (changed agg rows), `complete` (whole result).
- **Watermark** (`withWatermark("ts","10 minutes")`) bounds state for aggregations/joins and drops too-late events.
- **Checkpointing** (`checkpointLocation`) stores offsets + state → exactly-once with idempotent/transactional sinks (e.g., Delta).

## PySpark Idioms
- Use `F.col`, built-in `pyspark.sql.functions` over Python UDFs. If UDF needed, prefer **Pandas UDF** (vectorized Arrow) over row-at-a-time.
- Chain transforms; `withColumn` per-column in loops is fine but prefer `select` with many exprs for wide changes.
- `df.write.mode("overwrite").partitionBy("dt").parquet(path)`.
- Read only needed columns; push filters early.

## Tuning
- **Partitions**: keep ~128MB each; set `shuffle.partitions` accordingly.
- **Executor sizing**: ~4–5 cores/executor (beyond ~5, HDFS/IO contention); memory ≈ cores × per-task need + overhead. Avoid one fat executor and avoid tiny 1-core executors.
- **Memory**: unified region for execution + storage; `spark.executor.memoryOverhead` for off-heap/Python. OOM often = overhead too low or skew.
- Enable AQE, dynamic allocation. Read parquet with pushdown. Use `explain()` to inspect plan.

## Spark SQL + Catalyst
- Register temp views (`createOrReplaceTempView`) → query with `spark.sql(...)`; DataFrame API and SQL compile to the same optimized plan.
- **Catalyst** phases: analysis → logical optimization (predicate pushdown, column pruning, constant folding) → physical planning (join strategy) → **Tungsten** whole-stage codegen.
- Inspect with `df.explain(True)` / `explain("formatted")`; look for `Exchange` (shuffle), `BroadcastExchange`, `Sort`, scan-level `PushedFilters`/`ReadSchema`.
- **Partition pruning** kicks in when filtering on a partition column of a partitioned source.

## Common Actions/Transforms
- Actions: `count`, `collect`, `take(n)`, `first`, `show`, `write`, `foreach`, `reduce`, `saveAsTable`.
- Wide transforms: `groupBy`, `join`, `distinct`, `dropDuplicates`, `repartition`, `orderBy`, `agg`, window functions.
- Narrow: `select`, `filter`/`where`, `withColumn`, `map`, `union`, `sample`.
- `dropDuplicates(["k"])` dedupes; window `row_number()` gives "latest per key."

## Data Sources + Write Modes
- Read: `spark.read.parquet/json/csv/jdbc/format("delta")`; `.option("mergeSchema","true")` for evolving parquet.
- Write modes: `overwrite`, `append`, `error` (default), `ignore`. `partitionBy(...)` + `bucketBy(...)`.
- **Dynamic partition overwrite** (`spark.sql.sources.partitionOverwriteMode=dynamic`) overwrites only touched partitions → idempotent daily loads.
- JDBC reads: set `partitionColumn`, `lowerBound`, `upperBound`, `numPartitions` to parallelize, else single-threaded pull.

## Memory Model
- Executor memory split: **execution** (shuffles/joins/sorts/aggs) + **storage** (cache) share a unified region (evict each other), plus **user** memory + **reserved**.
- `spark.executor.memoryOverhead` (off-heap, ~10% or 384MB min) covers Python workers, network buffers — OOM-killed containers usually mean overhead too low.
- **Spill** to disk when execution memory exceeds budget → slow but survives; excessive spill signals under-partitioning/skew.

## Deployment + Submit
- `spark-submit --master yarn|k8s://... --deploy-mode cluster|client --num-executors --executor-cores --executor-memory --driver-memory app.py`.
- **client** mode: driver runs where you submit (dev/notebooks); **cluster** mode: driver runs inside the cluster (production).
- **Dynamic allocation** (`spark.dynamicAllocation.enabled`) adds/removes executors by load; needs external shuffle service.
- Key knobs: `spark.sql.shuffle.partitions`, `spark.sql.adaptive.enabled`, `spark.sql.autoBroadcastJoinThreshold`, `spark.executor.memoryOverhead`, `spark.default.parallelism`.

## Gotchas -> Fix
- **`collect()` / `toPandas()` on big data** → driver OOM → aggregate/sample first, or write to storage.
- **Shuffle blowup / 200 partitions default** on huge data → tune `spark.sql.shuffle.partitions` + enable AQE.
- **Executor OOM** → usually skew or too-large broadcast or low overhead → salt/AQE, lower broadcast threshold, raise `memoryOverhead`.
- **Small-files on write** → `coalesce(n)` or AQE + `OPTIMIZE`; don't over-partition output.
- **Python UDF slow** → replace with native function or Pandas UDF (Arrow).
- **Data skew straggler tasks** → enable `adaptive.skewJoin`, salt hot keys.
- **Cartesian/exploding join** (fan-out on non-unique key) → dedupe key or aggregate before join; check for missing join condition.
- **Recomputation** (same DF used many times, no cache) → `cache()`/`persist()` the reused branch.
- **Broadcast auto-disabled** on large dim → raise threshold or `broadcast()`; else full shuffle.
- **`count()` in logging** forces extra full jobs → avoid gratuitous actions.
- **Streaming state unbounded** (no watermark) → memory grows forever → add `withWatermark`.
- **Non-deterministic partitioning + append** → duplicate rows on retry → overwrite partition or use Delta MERGE.
- **`groupByKey` on RDD** shuffles all values → OOM → use `reduceByKey`/`aggregateByKey` (map-side combine) or DataFrame `groupBy().agg()`.
- **Too few partitions** → underutilized cores, huge tasks, spill → `repartition` up; too many tiny → `coalesce` down.
- **JDBC single-threaded read** → slow extract → set `partitionColumn`/bounds/`numPartitions`.
- **`explode` on nested arrays** balloons rows/memory → filter first, control partition count after.
- **Wide `withColumn` in long loops** builds a giant plan → slow analysis/StackOverflow → batch into one `select`.
- **AQE disabled on old cluster** → static 200 shuffle partitions + no skew fix → upgrade/enable `spark.sql.adaptive.enabled`.

## Delta Lake with Spark
- ACID over Parquet: `df.write.format("delta")`, `MERGE INTO` for upserts, `OPTIMIZE ... ZORDER BY (col)` to compact + cluster, `VACUUM` to purge old files.
- Time travel: `spark.read.option("versionAsOf", n)` or `timestampAsOf`. Schema enforcement blocks bad writes; `mergeSchema` to evolve.
- Idempotent streaming sink: checkpoint + Delta = exactly-once.
