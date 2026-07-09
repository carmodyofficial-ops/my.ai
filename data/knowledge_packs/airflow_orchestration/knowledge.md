# Airflow Orchestration

## Core Objects
- **DAG**: directed acyclic graph of tasks + scheduling metadata. Defined in Python; the file is parsed repeatedly by the scheduler.
- **Task**: a single unit = an instantiated **Operator**. **TaskInstance** = task for a specific run (dag_run).
- **Operators**: `PythonOperator`, `BashOperator`, `KubernetesPodOperator`, provider operators (`SnowflakeOperator`, `S3ToRedshift`, etc.). **Sensors** wait for a condition.
- **DagRun**: one execution of the DAG for a logical date.

## Scheduling
- `schedule` (formerly `schedule_interval`): cron (`"0 2 * * *"`), preset (`@daily`), `timedelta`, or dataset-driven.
- **logical_date** (a.k.a. `execution_date` / `ds`): the START of the interval, not wall-clock run time. A `@daily` run for 2026-07-08 fires **after** 2026-07-08 ends (at 00:00 2026-07-09). This trips everyone up.
- `data_interval_start` / `data_interval_end` are the modern, clearer fields — use these to bound extracts.
- **catchup**: `catchup=True` backfills every missed interval since `start_date`; `catchup=False` runs only the latest. Set `catchup=False` unless you truly want backfill on deploy.
- `start_date` should be static (not `datetime.now()` — that makes it never schedule). No `end_date` = runs forever.
- `max_active_runs`, `depends_on_past`, `wait_for_downstream` control concurrency/ordering across runs.

## Dependencies
- Bit-shift: `a >> b >> c` (a then b then c); `[a,b] >> c` (fan-in); `a >> [b,c]` (fan-out).
- **TaskFlow API** (`@task`, `@dag`): return value of one `@task` passed as arg to another auto-wires dependency + XCom. Cleaner than explicit operators for Python logic.
```python
@task
def extract(): return url_data
@task
def transform(data): ...
transform(extract())
```
- `trigger_rule` (`all_success` default, `all_done`, `one_failed`, `none_failed_min_one_success`) controls when a task runs given upstream states.

## XCom
- Cross-task communication: small key/value pushed to metadata DB, pulled downstream. `ti.xcom_push/pull` or TaskFlow return values.
- **For small metadata only** (ids, counts, paths) — NOT dataframes/files. Backed by DB; large payloads bloat it. Use external storage (S3) + pass the path via XCom.

## Sensors
- Wait for external state: `S3KeySensor`, `ExternalTaskSensor`, `SqlSensor`, `FileSensor`.
- Use `mode="reboot"`... actually **`mode="reschedule"`** frees the worker slot between checks (vs `poke` which holds it). Long waits with `poke` → slot exhaustion/deadlock.
- Prefer **deferrable operators/sensors** (async triggerer) for long waits — near-zero worker usage.
- Always set `timeout` to avoid infinite waits.

## Retries + SLAs
- Per-task: `retries`, `retry_delay`, `retry_exponential_backoff`, `max_retry_delay`.
- `execution_timeout` caps task duration. `on_failure_callback`/`on_retry_callback` for alerting.
- **SLA**: `sla=timedelta(...)` — miss triggers an SLA-miss callback/alert (does NOT kill the task).

## Connections / Variables / Hooks
- **Connections**: stored credentials/endpoints (`conn_id`), referenced by hooks/operators. Keep secrets in a backend (Vault/Secrets Manager), not code.
- **Variables**: key/value config; avoid `Variable.get()` at top level (parsed every DAG parse → DB hammering) — fetch inside tasks or use Jinja templating.
- **Hooks**: reusable interface to external systems (`PostgresHook`, `S3Hook`), used inside operators.

## Idempotency + Backfill
- Tasks must be idempotent — rerun/backfill re-executes them. Overwrite target partition keyed by `data_interval_start`, or MERGE.
- Backfill via `airflow dags backfill -s ... -e ...` or `catchup=True`. Parameterize all IO by logical/interval date, never `now()`.

## Dynamic Task Mapping
- `.expand()` creates tasks at runtime from a list: `process.expand(file=list_files())` → one mapped task instance per element. Enables data-dependent fan-out without static loops.

## Executors
- **LocalExecutor**: single machine, parallel via subprocesses. Small setups.
- **CeleryExecutor**: distributed workers via broker (Redis/RabbitMQ). Horizontal scale.
- **KubernetesExecutor**: one pod per task — isolation, per-task resources, no idle workers. Good for bursty/heterogeneous.
- **CeleryKubernetes** hybrid exists. SequentialExecutor = testing only.

## Templating (Jinja)
- Fields marked templated render Jinja at runtime with the context: `{{ ds }}` (logical date `YYYY-MM-DD`), `{{ ds_nodash }}`, `{{ data_interval_start }}`, `{{ data_interval_end }}`, `{{ params.x }}`, `{{ var.value.my_key }}`, `{{ ti }}`, `{{ macros.ds_add(ds, -7) }}`.
- Templating happens at **execution**, so `Variable.get` via `{{ var.value.x }}` avoids the parse-time DB hit of calling `Variable.get()` in Python at top level.
- Use templated `sql`/`bash_command`/op_kwargs to parameterize by run date → idempotent, backfillable.

## DAG Anatomy
```python
with DAG(dag_id="etl", start_date=datetime(2026,1,1),
         schedule="0 2 * * *", catchup=False,
         default_args={"retries":2, "retry_delay":timedelta(minutes=5)}) as dag:
    extract() >> transform() >> load()
```
- `default_args` apply to all tasks (retries, owner, callbacks). `tags`, `doc_md`, `max_active_runs` on the DAG.
- One DAG per logical pipeline; keep task count reasonable (thousands of tasks/DAG strain the scheduler/UI).

## Datasets + Data-Aware Scheduling
- **Dataset**: declare a task `outlets=[Dataset("s3://.../table")]`; downstream DAG `schedule=[that_dataset]` triggers when it updates → event-driven cross-DAG dependencies without sensors.
- Replaces brittle `ExternalTaskSensor` polling for producer→consumer DAG links.

## Pools + Concurrency
- **Pools** cap concurrent tasks hitting a shared resource (e.g. `pool="warehouse"` slots=5).
- `max_active_tasks` (per DAG), `max_active_runs` (concurrent DAG runs), `parallelism` (deployment-wide), per-task `priority_weight`.

## TaskGroups + Organization
- **TaskGroup** (`with TaskGroup("stage") as tg:`) visually/logically groups tasks in the UI (replaces deprecated SubDAGs — SubDAGs caused deadlocks, avoid).
- **Edge labels** annotate dependencies; **`chain()`/`cross_downstream()`** helpers wire complex graphs programmatically.
- Split unrelated pipelines into separate DAGs; use Datasets or `TriggerDagRunOperator` for cross-DAG triggers.

## Deferrable Operators / Triggerer
- **Deferrable** operators suspend to the async **triggerer** process while waiting (e.g. `S3KeySensorAsync`, `TimeDeltaSensorAsync`, deferrable `KubernetesPodOperator`), freeing the worker slot entirely.
- Use for long external waits (jobs, file arrival) at scale — far cheaper than `poke` sensors holding workers.

## Testing + Local Dev
- `airflow dags list-import-errors` catches parse errors; `airflow tasks test <dag> <task> <date>` runs a single task without scheduler/DB state.
- Unit-test callables as plain Python; keep business logic out of operators for testability.
- CI: parse all DAGs, lint, run `pytest` on task functions.

## Common Operators
- `PythonOperator`/`@task`, `BashOperator`, `EmptyOperator` (no-op join point), `BranchPythonOperator` (conditional path via returned task_id), `ShortCircuitOperator` (skip downstream if False), `TriggerDagRunOperator`, `KubernetesPodOperator`, provider transfer/SQL operators.
- **Branching**: skipped branches propagate `skipped`; downstream join needs `trigger_rule="none_failed_min_one_success"` to still run.

## Components
- **Scheduler**: parses DAGs, creates DagRuns/TaskInstances, queues ready tasks. **Executor**: runs queued tasks. **Webserver**: UI. **Metadata DB** (Postgres): state of everything. **Triggerer**: async waits for deferrable operators.
- Task states: `none → scheduled → queued → running → success/failed/up_for_retry/skipped/upstream_failed`. Clear a task to rerun it (and downstream).

## Gotchas -> Fix
- **Heavy top-level code** (imports, API calls, `Variable.get`, big computations at module scope) runs on **every DAG parse** (seconds) → slow scheduler, DB load → move work inside tasks/callables; keep top level light.
- **execution_date/logical_date confusion** — run "for 2026-07-08" starts after that day ends → use `data_interval_start/end` to bound extracts; expect the lag.
- **catchup=True surprise backfill** on first deploy floods scheduler → set `catchup=False` deliberately.
- **`start_date=datetime.now()`** → DAG never schedules (interval end never reached) → use a fixed past date.
- **Non-idempotent task** appends dupes on retry/backfill → overwrite-partition or MERGE keyed by interval.
- **Large XCom** (dataframe) bloats metadata DB → pass S3 path, store data externally.
- **Sensor in `poke` mode for hours** exhausts worker slots (deadlock) → `mode="reschedule"` or deferrable sensors + `timeout`.
- **Dynamic `start_date`/`schedule` from variables** → nondeterministic scheduling → keep static.
- **Timezone naive datetimes** → set `default_timezone`/use `pendulum` UTC; store/compute in UTC.
- **Tasks sharing local state / relying on execution order not in deps** → declare explicit dependencies; tasks may run on different workers.
- **Unbounded parallelism** overwhelms downstream DB → set `max_active_tasks`, pools, `max_active_runs`.
- **Secrets in DAG code** → use Connections + a secrets backend.
- **SubDAGs** → deadlocks/slot starvation → use TaskGroups instead.
- **Branch join task skipped** (default `all_success` sees skipped upstream) → set `trigger_rule="none_failed_min_one_success"`.
- **`depends_on_past` deadlock** (one failed run blocks all future) → use sparingly; clear the failed run or drop the flag.
- **Too many tasks/DAG or overly frequent schedule** strains scheduler → consolidate, use dynamic mapping, raise parse/heartbeat intervals.
