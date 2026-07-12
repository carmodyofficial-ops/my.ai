# Performance Optimization Reference

## Golden rule
Profile -> fix the **biggest** hotspot -> re-measure -> repeat. Never guess; intuition about hotspots is usually wrong. Correctness + clarity first; optimize only what data proves.

## Measure first
- Profile before touching anything: `cProfile`/`py-spy`, `perf`, flamegraphs, `EXPLAIN ANALYZE`, `pprof`, browser DevTools, distributed tracing. Optimize the line/function eating the most **wall-clock**.
- **Amdahl's law**: max speedup = `1/((1-p)+p/s)` where `p` = parallelizable/optimizable fraction. A 2x win on 3% of runtime = ~1.5% total. Optimizing a non-bottleneck is wasted work.
- Measure the **right metric**: throughput vs latency vs tail (p50 vs **p99/p99.9** — tail dominates user experience and fan-out systems). Watch percentiles, not averages (averages hide tail).
- Set a target; **stop when met**. Benchmark on representative data/hardware, warm caches/JIT, repeat runs, control noise.

## Latency numbers (order of magnitude, know the ratios)
- L1 ~1ns, L2 ~4ns, main memory ~100ns, SSD read ~16us, network round-trip in-DC ~0.5ms, disk seek ~2ms, cross-continent RTT ~150ms.
- Memory is ~100x cache; disk/network is ~10^4-10^6x memory. **Crossing a boundary (mem->disk->network) dwarfs any in-CPU tweak.** Optimize the outermost boundary first.

## Wins, in order of payoff
1. **Algorithmic**: `O(n^2)->O(n log n)->O(n)` crushes any constant-factor tweak. Fix Big-O first. Hash lookup replaces nested scan.
2. **Kill N+1**: batch the query/call — one `WHERE id IN (...)` not 100 selects. Same for HTTP/RPC/syscalls. The classic hidden 100x.
3. **Batching**: amortize round-trips — bulk insert, `pipeline()`, chunked reads, coalesce writes.
4. **Index** columns you filter/join/sort on; verify with `EXPLAIN` (seq scan -> index scan). Watch write/index-maintenance cost. Covering index avoids table lookups.
5. **Cache/memoize** pure, hot, expensive results — **but own invalidation** (TTL or explicit bust). A stale cache is a bug, not a speedup. Layers: CPU cache, app memory, Redis, CDN. Watch **thundering herd / cache stampede** on expiry.
6. **Async/parallel for IO**; **pool connections** (never open-per-request); reuse TCP/keep-alive.
7. **Stream/lazy** large data — generators, cursors, pagination. Don't load 1GB to sum a column.
8. **Precompute** when read-heavy; compute-on-demand when write-heavy or rarely read. Denormalize for read paths knowingly.
9. **Right structure + data locality**: set for membership, deque for queue, contiguous arrays over pointer-chasing.

## CPU-level
- **Cache locality** dominates: sequential/contiguous access + small working set. **Array-of-structs vs struct-of-arrays** — SoA lets you stream only the fields you touch. Pointer-chasing (linked lists, scattered objects) = cache misses.
- **Branch prediction**: unpredictable branches stall the pipeline (~15-20 cycle flush). Sort data to make branches predictable; use branchless/`cmov`, lookup tables.
- **SIMD/vectorization**: process 4-16 lanes per instruction; needs contiguous data + no dependency chains. Rely on autovectorization or intrinsics/libs.
- **False sharing**: per-thread counters on one cache line -> ping-pong. Pad to 64B.
- Reduce work in the hot loop: hoist invariants, avoid virtual dispatch/allocation/bounds-checks in inner loops.

## Memory / allocation / GC
- **Allocation is not free**: churn -> GC pressure, fragmentation, cache pollution. **Pool/reuse** buffers; preallocate to known size; **object pools** for hot short-lived objects.
- Minimize garbage in hot paths; prefer value types/stack/arena allocation; avoid boxing. Reserve capacity (`list(cap)`, `make([]T,0,n)`) to dodge repeated grow+copy.
- GC tradeoffs: throughput vs pause; large heaps -> long pauses. Reduce allocation rate before tuning the collector.

## IO
- **Async** to overlap waits; **batch** to amortize round-trips; **compress** to trade CPU for bandwidth.
- Sequential > random IO. Buffer/chunk reads/writes. **Chatty IO** (many tiny calls) is the #1 remote perf killer — coalesce.

## Profiling techniques
- **Sampling profiler** (`perf`, `py-spy`, `async-profiler`): low overhead, statistical, safe in prod — best first tool. **Instrumenting profiler** (`cProfile`): exact call counts, high overhead, distorts timings.
- **Flame graph**: width = time; wide plateaus = hotspots. **Off-CPU/wall-clock** profiling reveals blocking/waiting that CPU profiles miss.
- **Micro vs macro**: microbenchmark a kernel (JMH, `pytest-benchmark`, `criterion`) only after the macro profile points to it. Always profile a build with optimizations on, realistic data, warmed caches/JIT.
- **RED/USE metrics** + tracing for services: Rate/Errors/Duration, Utilization/Saturation/Errors. Find the saturated resource (CPU, IO, lock, GC).

## Database performance
- **Index** for filter/join/sort; composite index column order matters (equality then range). `EXPLAIN` — kill seq scans on big tables. Too many indexes slow writes.
- **Kill N+1** (eager-load/join), select only needed columns (no `SELECT *`), paginate with keyset (`WHERE id > ?`) not `OFFSET` on deep pages.
- **Connection pool** (never connect-per-request); **prepared statements** (parse once, plan cache); batch writes; keep transactions short to reduce lock hold.
- Read replicas / caching layer for read-heavy; denormalize knowingly. Watch lock contention + row/table locks under concurrency.

## Concurrency & compression for throughput
- Overlap IO waits with async/threads; parallelize CPU work across cores (mind Amdahl + coordination cost).
- **Compress** to trade CPU for bandwidth/storage when network/disk-bound; skip it when already CPU-bound or data is tiny/incompressible.
- **CDN / edge caching** for static + cacheable responses cuts RTT to the user.

## In-loop discipline
- Hoist invariant work **out** of loops. Never string-concat in a loop -> build list, `join` once. Don't re-query, re-compile regex, or re-allocate per iteration.
- Reserve capacity before filling; avoid per-iteration allocation, virtual dispatch, and repeated attribute/property lookups in hot loops.

## Gotchas -> Fix
- **Optimizing the non-bottleneck** -> profile first; obey Amdahl.
- **Micro-optimizing a slow-language/interpreted path** -> rewrite the hot kernel/SQL, or vectorize, rather than shaving cycles by hand.
- **Premature optimization wrecks readability** -> keep the simple version until data demands more.
- **Cache with no invalidation story** -> stale reads -> define TTL/bust up front; guard against stampede (single-flight, jittered TTL).
- **Ignoring Big-O while polishing constants** -> fix the algorithm first.
- **Micro-benchmark lies**: dead-code elimination, unwarmed JIT, cache-hot data, tiny N, no variance -> benchmark realistic size/warm state; measure the whole system, watch p99.
- **N+1 hidden by an ORM / lazy loading** -> eager-load/join, inspect emitted SQL.
- **Cache misses from pointer-chasing** -> contiguous layout, SoA, reduce indirection.
- **Chatty remote IO** -> batch/coalesce; reduce round-trips.
- **GC pauses from allocation churn** -> pool/reuse, reduce allocation rate before tuning GC.
- **Optimizing average, ignoring tail** -> tail latency + fan-out amplify -> measure/fix p99.
- **Contention added by "parallelizing"** -> lock/false-sharing overhead can make it slower -> measure; shard state.
- **Speedup that breaks correctness** -> keep a reference impl + regression test around the fast path.

## Concurrency & scaling
- **Vertical** (bigger box) is simplest; **horizontal** (more nodes) scales further but needs statelessness + load balancing. Cache/CDN before scaling out.
- **Contention** is the parallel tax: locks, false sharing, cache-line bouncing, shared counters. Shard state, use per-core/thread-local accumulators, merge at the end.
- **Little's law**: `L = λ x W` (in-flight = arrival rate x latency). Cut latency or cap concurrency to control queue depth; unbounded queues turn overload into latency collapse.
- Load test at realistic concurrency; find the knee where latency rises sharply (saturation) and set limits below it.

## Decision
Unprofiled -> profile. Bottleneck clear -> fix biggest, measure after. Keep the simple version unless data demands more.
