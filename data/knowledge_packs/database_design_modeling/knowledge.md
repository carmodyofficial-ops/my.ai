# Database Design & Data Modeling

Design schema from **access patterns + integrity needs**, not just "what the data is".

## Normalization (remove redundancy/anomalies)
- **1NF**: atomic values, no repeating groups/arrays in a column, each row unique (PK). No `phones = "a,b,c"`.
- **2NF**: 1NF + no partial dependency — every non-key attr depends on the **whole** composite key (split attrs that depend on part of key).
- **3NF**: 2NF + no transitive dependency — non-key attrs depend only on the key, not on other non-key attrs (move `zip→city` derivable data out).
- **BCNF**: stricter 3NF — every determinant is a candidate key. Handles overlapping candidate keys.
- Higher: 4NF (multivalued deps), 5NF (rare).
- Goal: each fact stored once → no update/insert/delete anomalies.

## Denormalization (deliberate redundancy for read speed)
- Duplicate/precompute (store `order_total`, `author_name`) to avoid joins on hot reads.
- Costs: extra storage, must keep copies in sync (triggers/app/materialized views), write amplification.
- Use when: read-heavy, join cost dominates, reporting/OLAP. Normalize first, denormalize with evidence.

## Keys
- **Primary key**: unique + non-null row identifier.
- **Surrogate** (auto `BIGINT`/`UUID`, no business meaning) vs **natural** (email, SSN). Prefer surrogate: stable, small, immutable; natural keys change and leak PII.
- **Foreign key**: references another table's PK → referential integrity + `ON DELETE CASCADE/RESTRICT/SET NULL`.
- **Composite key**: multiple columns (common in junction tables).
- **Candidate/alternate key**: `UNIQUE` constraint on natural identifier alongside surrogate PK.
- UUID PK: v7/ULID (time-ordered) avoid random-UUID index fragmentation; v4 random hurts B-tree locality.

## Relationships & ER modeling
- **1:1** — same table or split (rarely needed; use for optional/large columns).
- **1:many** — FK on the "many" side (post → user_id).
- **many:many** — **junction/associate table** with two FKs as composite PK (`enrollment(student_id, course_id)`), plus relationship attributes (grade, enrolled_at).
- ER: entities (tables), attributes (columns), relationships (FKs), **cardinality** (1/N) + **participation** (mandatory/optional). Cardinality error is the classic modeling bug.

## Indexing strategy
- **B-tree** (default): equality + range + `ORDER BY` + prefix of composite. **Hash**: equality only.
- **Composite** order = ESR / most-selective-and-equality first; leftmost-prefix rule.
- **Covering index** (`INCLUDE` cols / all needed columns) → index-only scan, no heap fetch.
- **Selectivity**: index high-cardinality columns; low-cardinality (bool, status) rarely helps alone (use partial index `WHERE active`).
- Index FKs (not automatic in many DBs) to speed joins + cascade.
- Cost: every index slows writes + uses space. Index for real queries; drop unused (`pg_stat_user_indexes`).

## Constraints & data types
- `NOT NULL`, `UNIQUE`, `CHECK (age>=0)`, `FK`, `DEFAULT`, `PRIMARY KEY`. Enforce invariants in DB, not only app.
- Types: exact `NUMERIC/DECIMAL` for **money** (never `FLOAT` — rounding errors); `TIMESTAMPTZ` for time (store UTC); `INT`→`BIGINT` before overflow; `TEXT`/`VARCHAR(n)`; native `ENUM`/lookup table; `JSONB` for sparse/dynamic; `BOOLEAN`. Narrow types = smaller rows, faster.

## Read vs write modeling
- **OLTP** (transactional): normalized, many small indexed writes, short queries. Normalize.
- **OLAP** (analytics/warehouse): denormalized **star schema** (fact table + dimension tables) / snowflake; columnar; batch load; wide scans. Optimize for aggregation reads.
- CQRS: separate write model (normalized) from read model (denormalized projections/materialized views).

## Migrations
- Versioned, incremental, forward-only where possible (Flyway/Liquibase/Alembic/Prisma). One change per migration, reversible when feasible.
- **Expand-contract** for zero-downtime: add nullable col/new table (expand) → dual-write/backfill → switch reads → drop old (contract). Never rename/drop in one deploy with running old code.
- Big tables: add index `CONCURRENTLY`, backfill in batches, add `NOT NULL` after backfill with validated `CHECK`.

## Common modeling patterns
- **Lookup/reference table** for enums/categories → FK, editable without schema change.
- **Polymorphic association** (comment on post OR photo): options — exclusive FK columns + CHECK, shared supertable, or `(entity_type, entity_id)` (weak integrity). Prefer typed FK columns.
- **Hierarchies/trees**: adjacency list (`parent_id`), materialized path (`/1/4/9/`), nested set, or recursive CTE / Postgres `ltree`.
- **Soft delete**: `deleted_at TIMESTAMPTZ NULL` + partial index/filter — keeps history, complicates uniqueness/queries.
- **Audit/history**: separate `_history` table or temporal columns (`valid_from/valid_to`), triggers or app.
- **Slowly changing dimensions** (warehouse): SCD Type 2 = new row per change with effective dates + current flag.
- **Multi-tenancy**: shared table + `tenant_id` (index it, RLS) vs schema-per-tenant vs DB-per-tenant — tradeoff isolation vs ops.

## Sizing & keys detail
- **Composite PK column order** matters for the clustered/index layout — put the column you range/filter on first.
- **Clustered index** (PK in InnoDB / clustering in SQL Server) determines physical row order → sequential PK avoids page splits.
- `TIMESTAMPTZ` vs `TIMESTAMP`: store timezone-aware UTC, convert at edges. `DATE` vs `TIMESTAMP` — don't overstate precision.
- Choose smallest type that fits the domain + headroom (`SMALLINT`/`INT`/`BIGINT`); `CHAR(n)` only for true fixed-width.

## Gotchas -> Fix
- **Over-normalization** → 8-way joins on every read, slow. Fix: denormalize hot paths / materialized views; balance integrity vs read cost.
- **Wrong cardinality** (1:many modeled as 1:1, or missing junction for many:many) → can't represent data / duplicated rows. Fix: re-derive from real relationships; add junction table for M:N.
- **Missing indexes on FK/filter/sort columns** → seq scans, slow joins. Fix: index FKs and every WHERE/JOIN/ORDER BY column; verify with `EXPLAIN`.
- **`FLOAT` for money** → rounding errors. Fix: `NUMERIC(precision, scale)` or integer minor units (cents).
- **Nullable everything / no constraints** → dirty data, app must defend everywhere. Fix: `NOT NULL`, `CHECK`, `FK`, `UNIQUE` in schema.
- **Natural key as PK** (email/phone) that later changes → cascade updates everywhere. Fix: surrogate PK + unique constraint on natural key.
- **Storing CSV/JSON blob instead of rows** (violates 1NF) → can't query/index/join. Fix: separate rows/child table; JSONB only for truly dynamic sparse data.
- **EAV (entity-attribute-value) for everything** → unqueryable, no types. Fix: proper columns; JSONB for the genuinely dynamic subset.
- **Random UUID v4 PK** on huge table → index bloat, poor cache locality. Fix: ULID/UUIDv7 (time-ordered) or BIGINT identity.
- **No `ON DELETE` policy** → orphan rows or FK violations. Fix: explicit `CASCADE`/`RESTRICT`/`SET NULL` per semantics.
- **Enum as native type** hard to alter → migration pain. Fix: lookup/reference table for evolving sets.
- **Blocking migration** (rewrite table, add NOT NULL default on huge table, exclusive-lock index build) → downtime. Fix: expand-contract, `CREATE INDEX CONCURRENTLY`, batched backfill.
- **Too many indexes** → slow writes, bloat, wasted RAM. Fix: keep only indexes real queries use; drop unused; a compound index can replace several single-column ones.
- **Low-selectivity index alone** (boolean/status) rarely used by planner. Fix: partial index `WHERE status='active'`, or composite with a selective leading column.
- **Missing `UNIQUE` on business key** → duplicate rows slip in. Fix: unique constraint (composite if needed) enforced in DB.
- **Composite key/index in wrong column order** → leftmost-prefix can't serve queries. Fix: order by equality-then-range / most-selective; match query shape.
- **Soft-delete breaks unique constraints** (can't re-add "deleted" value). Fix: partial unique index `WHERE deleted_at IS NULL`.
- **UUID stored as text** not native/binary → bloated index, slow. Fix: native `UUID`/`BINARY(16)` type.
- **Boolean flags proliferating** (is_x, is_y, status_z) → inconsistent states. Fix: single `status` enum/lookup + CHECK on valid transitions.

## Indexing & query cost cues
- `EXPLAIN (ANALYZE, BUFFERS)` → look for Seq Scan on big tables, high `rows removed by filter`, nested-loop over unindexed join.
- **Cardinality/selectivity** drives index value: index columns where a value matches few rows. Keep stats fresh (`ANALYZE`).
- **Covering / index-only scan**: include all queried columns (`INCLUDE`) to skip heap fetch.
- Foreign-key columns should almost always be indexed (joins + cascade + lock avoidance).
