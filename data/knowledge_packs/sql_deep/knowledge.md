# Advanced SQL

## JOINs
- `INNER` matched rows only. `LEFT`/`RIGHT` keep all rows of one side, NULLs for missing other side. `FULL` keeps both. `CROSS` = cartesian.
- Put right-table filters in `ON`, not `WHERE`: on a LEFT JOIN, `WHERE b.col='x'` drops the NULL rows and silently turns it into an INNER join. Filter that survives outer join goes in `ON`.
- **Anti-join** (rows in A with no match in B): `LEFT JOIN b ON a.id=b.a_id WHERE b.a_id IS NULL`, or `WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.a_id=a.id)`. Prefer `NOT EXISTS` — NULL-safe (see below).
- **Semi-join** (rows in A that have ≥1 match, no dupes/no columns from B): `WHERE EXISTS (SELECT 1 FROM b WHERE b.a_id=a.id)`. A plain INNER JOIN fan-outs and duplicates A when B matches many.
- Self-join: `FROM emp e JOIN emp m ON e.mgr_id=m.id`. Join key type mismatch → implicit cast → no index.

## Window functions
`f() OVER (PARTITION BY g ORDER BY t [frame])` — computes per row, does NOT collapse rows (unlike GROUP BY).
- Ranking: `ROW_NUMBER()` unique 1..n; `RANK()` gaps after ties (1,1,3); `DENSE_RANK()` no gaps (1,1,2); `NTILE(4)` buckets.
- Offset: `LAG(c, 1, dflt)` prev row, `LEAD(c)` next; `FIRST_VALUE`/`LAST_VALUE`/`NTH_VALUE`.
- **Frames**: default with `ORDER BY` is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — running total. For a moving window use `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`. `RANGE` groups peer (equal-ORDER-value) rows together; `ROWS` counts physical rows — a frequent bug source with duplicate order keys.
- `LAST_VALUE` needs `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` or it returns the current row (default frame ends at current row).
- Dedupe keep-latest: `QUALIFY ROW_NUMBER() OVER(PARTITION BY key ORDER BY ts DESC)=1` (or wrap in subquery where no `QUALIFY`).
- Cannot reference a window alias in `WHERE`/`GROUP BY` (computed after) — wrap in CTE/subquery.

## CTEs & recursion
`WITH x AS (...), y AS (...) SELECT ...`. Readability + reuse. Postgres ≤11 materializes CTEs (optimization fence); 12+ inlines unless `MATERIALIZED`.
```sql
WITH RECURSIVE t AS (
  SELECT id, parent_id, 1 lvl FROM node WHERE parent_id IS NULL   -- anchor
  UNION ALL
  SELECT n.id, n.parent_id, t.lvl+1 FROM node n JOIN t ON n.parent_id=t.id  -- recursive
) SELECT * FROM t;
```
Needs anchor + termination; `UNION` (not ALL) or a depth guard prevents cycle loops.

## GROUP BY / HAVING / GROUPING SETS
- `WHERE` filters before aggregation, `HAVING` after (`HAVING count(*)>1`).
- Every non-aggregated SELECT col must be in GROUP BY (Postgres strict; MySQL's `ONLY_FULL_GROUP_BY` off = picks arbitrary row).
- `GROUPING SETS`, `ROLLUP(a,b)` (hierarchical subtotals + grand total), `CUBE(a,b)` (all combos) in one pass; `GROUPING(col)` flags the total rows.
- `FILTER (WHERE ...)` for conditional aggregates: `count(*) FILTER (WHERE status='x')`.

## Subqueries vs JOINs
- Correlated subquery executes per outer row — often slow; planner may or may not decorrelate. Prefer JOIN/window.
- `EXISTS` short-circuits on first match, beats `IN` on large subqueries and is NULL-safe.
- Scalar subquery in SELECT returning >1 row errors; returning 0 rows → NULL.

## Indexes
- B-tree serves `=`, `<`, `>`, `BETWEEN`, `IN`, prefix `LIKE 'abc%'`, and ORDER BY (sorted). Not `LIKE '%x'`, not `col+1=5`, not function on col unless expression index.
- **Composite order**: equality columns first, then the range/sort column: `(status, created_at)` serves `status='x' AND created_at>...` and its ORDER BY. Column order matters — leftmost-prefix rule.
- **Covering**: index contains all needed columns → index-only scan, no heap fetch. Postgres `INCLUDE (c)` adds payload cols without affecting key order.
- Partial index: `WHERE active` — smaller, for skewed predicates.
- Index FKs (Postgres does NOT auto-index them) — unindexed FK = slow cascade + lock contention.
- **When NOT to index**: low-cardinality cols (boolean), small tables (seq scan cheaper), write-heavy tables (every index taxes INSERT/UPDATE/DELETE), rarely-filtered cols.

## Query plans
- `EXPLAIN` = estimate; `EXPLAIN (ANALYZE, BUFFERS)` = runs it + real timings/rows/IO.
- **Seq Scan** fine for small/most-of-table; bad when index should apply. **Index Scan** / **Index Only Scan** targeted. **Bitmap Heap Scan** for medium selectivity.
- Nested Loop good for few rows; Hash Join / Merge Join for large sets. Big gap between estimated and actual rows → stale stats (`ANALYZE`) or bad correlation.

## Transactions & isolation
- Levels (weak→strong): Read Uncommitted, Read Committed (PG default), Repeatable Read, Serializable.
- Anomalies: dirty read, non-repeatable read, phantom, write skew. Higher isolation removes more but raises serialization-failure retries. Postgres RR already blocks phantoms (snapshot); write skew needs Serializable.
- Keep transactions short; long ones bloat MVCC and hold locks. Always be ready to retry on `40001` serialization failure.

## UPSERT / MERGE
- Postgres: `INSERT ... ON CONFLICT (id) DO UPDATE SET c=EXCLUDED.c` (or `DO NOTHING`). Needs a unique/exclusion constraint on the conflict target.
- SQL standard / SQL Server / PG15+: `MERGE INTO t USING s ON ... WHEN MATCHED THEN UPDATE WHEN NOT MATCHED THEN INSERT`.

## NULL semantics (three-valued logic)
- Any comparison with NULL → UNKNOWN, filtered out. Use `IS NULL` / `IS DISTINCT FROM`.
- `NULL = NULL` is UNKNOWN, not true. Aggregates skip NULL (except `count(*)`).
- `x NOT IN (subquery containing any NULL)` → **zero rows** (the classic bug): use `NOT EXISTS`.

## Set ops
`UNION` dedupes (sort/hash, costly); `UNION ALL` cheap, use when disjoint. `EXCEPT`, `INTERSECT`. Column count/types must align.

## Pagination
- **Keyset/seek beats OFFSET**: `WHERE (created_at,id) < (:last_ts,:last_id) ORDER BY created_at DESC, id DESC LIMIT 20`. OFFSET n scans and discards n rows every page → O(n) drift.

## Gotchas → Fix
- `NOT IN` + NULL → zero rows → use `NOT EXISTS` / anti-join.
- Right-table filter in `WHERE` on LEFT JOIN → silent INNER → move to `ON`.
- Missing/wrong JOIN predicate → cartesian explosion → verify every join has a condition per table.
- Function/cast on indexed col (`WHERE date(ts)=...`, `int_col='5'`) → index unused → rewrite as range (`ts >= d AND ts < d+1`) or expression index.
- `SELECT *` → defeats covering index, breaks on schema change → name columns.
- Fan-out: INNER JOIN to one-to-many duplicates parent rows → use EXISTS or aggregate.
- N+1: per-row query in app loop → single JOIN / `WHERE id IN (...)` / batch.
- `count(DISTINCT ...)` after a fan-out join over-/under-counts → aggregate in a subquery first.
- `HAVING` used where `WHERE` would do → filters after aggregation, slower → push non-aggregate predicates to `WHERE`.
- Mixing `ORDER BY` without a tiebreaker for pagination → nondeterministic order → always append a unique tiebreak column.
