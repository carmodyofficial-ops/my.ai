# PostgreSQL-Specific Reference

## psql
- `\l` list DBs · `\dt` tables · `\d tbl` describe · `\di` indexes · `\df` functions · `\dn` schemas · `\du` roles
- `\timing on` show query time · `\x` expanded rows · `\e` edit in $EDITOR · `\i file.sql` run · `\copy` client-side COPY · `\conninfo`

## Types (prefer these)
- IDs: `GENERATED ALWAYS AS IDENTITY` (SQL-standard) over `serial`. Both use a sequence; **gaps are normal** (rollbacks/caching).
- `bigint` for IDs/counts; `text` over `varchar(n)` (no perf diff, no length guesswork).
- `timestamptz` **always** over `timestamp` — stores UTC, converts per session TZ. `timestamp` ignores TZ -> silent bugs.
- `numeric(12,2)` for money (never float). `uuid` (with `gen_random_uuid()`). `boolean` (`true`/`false`). Arrays: `int[]`, `text[]` (`'{1,2}'`, `arr[1]` 1-based, `= ANY(arr)`).
- `jsonb` (binary, indexable, dedups keys) over `json` (raw text).

## JSONB
- `->` returns jsonb, `->>` returns text: `data->'a'->>'b'`. Path: `#>`, `#>>`.
- `@>` contains: `data @> '{"k":1}'`. `?` key exists, `?|`/`?&` any/all keys.
- Update: `jsonb_set(data,'{a,b}','5')`; merge with `||`; remove key `data - 'k'`.
- **GIN index required** for `@>`/`?`: `CREATE INDEX ON t USING gin (data);` (use `jsonb_path_ops` for smaller, `@>`-only).

## Indexes
- B-tree default (`=`, ranges, sort, `LIKE 'x%'`). GIN for jsonb/arrays/full-text. GiST geo/ranges. BRIN huge append-only.
- Partial: `CREATE INDEX ON t(x) WHERE active;` · Expression: `CREATE INDEX ON t(lower(email));`
- `CREATE INDEX CONCURRENTLY` — no table lock; **use in prod** (slower, can't run in txn, may leave INVALID index on fail -> drop+retry).

## EXPLAIN
- `EXPLAIN (ANALYZE, BUFFERS) SELECT ...` runs it, shows real time + heap/shared block reads.
- **Seq Scan** = full scan (fine for small/most-rows); **Index Scan** uses index. Big gap between `rows=` estimate and `actual` => stale stats -> `ANALYZE`.

## Upsert / RETURNING
```sql
INSERT INTO t(id,x) VALUES(1,5)
ON CONFLICT (id) DO UPDATE SET x = EXCLUDED.x
RETURNING id;
```
- `ON CONFLICT DO NOTHING` to ignore. `RETURNING *` works on INSERT/UPDATE/DELETE.

## CTEs & Windows
- `WITH ... ` and `WITH RECURSIVE`. CTEs inline by default (PG12+); add `MATERIALIZED` to force a barrier.
- Windows: `row_number()/rank()/lag()/sum() OVER (PARTITION BY a ORDER BY b)`. `DISTINCT ON (a) ...` PG-only.

## Transactions / MVCC
- MVCC: readers never block writers. Isolation: Read Committed (default), Repeatable Read, Serializable (retry on `40001`).
- `SELECT ... FOR UPDATE` locks rows; `FOR UPDATE SKIP LOCKED` for queues.

## Extensions
`CREATE EXTENSION IF NOT EXISTS x;` — `pg_stat_statements` (top queries), `pgcrypto` (`crypt`, `gen_random_uuid`), `uuid-ossp`, `postgis`.

## Roles & Grants
- Roles = users+groups. `CREATE ROLE app LOGIN PASSWORD '..';` `GRANT SELECT ON t TO app;` `GRANT app TO bob;`
- New tables aren't auto-granted: `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app;`

## VACUUM / bloat
- UPDATE/DELETE leave dead tuples; autovacuum reclaims + updates stats. `VACUUM (VERBOSE, ANALYZE) t;`, `VACUUM FULL` rewrites (exclusive lock).
- **Long-open txns block autovacuum** -> bloat. Find: `pg_stat_activity` (`state='idle in transaction'`); always commit/rollback.

## Gotchas
- Use `timestamptz`, not `timestamp`. Missing GIN => slow `@>`. Sequence gaps expected.
- `CONCURRENTLY` for prod index builds. App connections are heavy (~per-conn process) -> cap them; front with **PgBouncer**.
