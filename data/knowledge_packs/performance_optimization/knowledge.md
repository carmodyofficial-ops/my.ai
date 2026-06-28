# Performance Optimization Reference

## Golden Rule
Profile -> fix the **biggest** hotspot -> re-measure -> repeat. Never guess.

## Measure First
- Profile before touching anything (`cProfile`, `perf`, flamegraphs, DB `EXPLAIN`). Intuition about hotspots is usually wrong.
- Optimize the line/function eating the most wall-clock. A 2x win on 3% of runtime is noise.
- Set a target; stop when met.

## Wins, In Order of Payoff
1. **Algorithmic**: O(n^2)->O(n log n) crushes any constant-factor tweak. Fix the Big-O first. Hash lookups over nested scans.
2. **Avoid N+1**: batch the query/call. One `WHERE id IN (...)` not 100 selects. Same for HTTP, RPC, syscalls.
3. **Batching**: amortize round-trips—bulk insert, `pipeline()`, chunked reads.
4. **Index** the columns you filter/join/sort on. Verify with `EXPLAIN`; watch write cost.
5. **Cache/memoize** pure, hot, expensive results—**but own invalidation** (TTL or explicit bust). A stale cache is a bug, not a speedup.
6. **Async/parallel for IO**; **pool connections** (never open-per-request).
7. **Stream/lazy** large data—generators, cursors, pagination. Don't load 1GB to sum a column.
8. **Precompute** when read-heavy; compute-on-demand when write-heavy or rarely read.
9. **Data locality + right structure**: set for membership, deque for queue, contiguous arrays over pointer chasing.

## In-Loop Discipline
- Hoist invariant work **out** of loops.
- Never string-concat in a loop -> build a list, `join` once.
- Don't re-query, re-compile regex, or re-allocate per iteration.

## Gotchas
- Optimizing code that isn't the bottleneck.
- Micro-opting a slow-language path (rewrite the hot kernel/SQL instead).
- Premature optimization that wrecks readability—**correctness + clarity first**.
- Caching with no invalidation story.
- Ignoring Big-O while polishing constants.

## Decision
If unprofiled -> profile. If clear -> measure after. Keep the simple version unless data demands more.
