# Advanced SQL

## JOINs
- INNER: matched only. LEFT: all left + NULLs for unmatched right.
- Self-join: `FROM emp e JOIN emp m ON e.mgr_id=m.id`.
- **Anti-join**: `LEFT JOIN b ON a.id=b.a_id WHERE b.a_id IS NULL`. Clearer than `NOT IN`.
- Filter right table in `ON`, not `WHERE`, or LEFT JOIN becomes INNER.

## Window funcs
`f() OVER (PARTITION BY x ORDER BY y)` — keeps rows.
- `ROW_NUMBER()` unique; `RANK()` gaps on ties; `DENSE_RANK()` none.
- `LAG/LEAD(c)` prev/next. `SUM(c) OVER(PARTITION BY g ORDER BY t)` running total.
- Dedupe: keep `ROW_NUMBER() OVER(PARTITION BY key ORDER BY ts DESC)=1`.

## CTEs
`WITH x AS (...) SELECT...`. Recursive for trees:
`WITH RECURSIVE t AS (base UNION ALL recurse FROM t JOIN..)`. Need base + termination.

## GROUP BY / HAVING
WHERE filters pre-aggregation; HAVING post (`HAVING count(*)>1`).

## Subqueries vs JOINs
Correlated subquery runs per-row (slow) — prefer JOIN/window. `EXISTS` beats `IN` on big sets.

## Indexes
- Index cols in WHERE, JOIN, ORDER BY.
- **Composite order**: equality cols first, range/sort last `(status, created_at)`.
- Covering index has all selected cols → index-only scan.
- Index FKs (often missed).

## EXPLAIN
`EXPLAIN ANALYZE` — watch Seq Scan on big tables, nested loop over many rows.

## Transactions
Isolation: Read Committed (default) < Repeatable Read < Serializable. Higher = fewer anomalies, more retries. Keep txns short.

## UPSERT
PG: `INSERT.. ON CONFLICT (id) DO UPDATE SET c=EXCLUDED.c`. Std: `MERGE`.

## NULL (three-valued)
NULL compares unknown. `NOT IN (subquery w/ any NULL)` → **zero rows**; use `NOT EXISTS`.

## Set ops
`UNION` dedupes (costly), `UNION ALL` fast, `EXCEPT`, `INTERSECT`.

## Pagination
**Keyset > OFFSET**: `WHERE id > :last ORDER BY id LIMIT 20`. OFFSET scans+discards N rows.

## Gotchas
- N+1: looping queries → one JOIN/`IN`.
- Cartesian product: missing JOIN condition.
- `SELECT *`: breaks covering indexes.
- Implicit cast (`int_col='5'`) kills index use.
