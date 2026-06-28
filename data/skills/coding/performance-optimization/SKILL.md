---
name: performance-optimization
description: "How to make code faster correctly: measure first to find the real hotspot, fix the biggest one (usually algorithmic / N+1), re-measure — never guess or micro-optimize blindly."
version: 1.0.0
category: Coding
tags: [performance, optimize, optimization, slow, speed up, profiling, bottleneck, latency, faster, scalability, big-o]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when code is (or must be) faster — a slow endpoint, a long-running job, a scaling concern. The goal is the biggest real win for the least risk, not blind tweaking.

## Procedure

1. MEASURE FIRST. Profile (cProfile/perf/flamegraph, DB EXPLAIN, timing logs) to find the line/function eating the most wall-clock. Intuition about the hotspot is usually wrong; a 2x win on 3% of runtime is noise.
2. Set a target (e.g. "p95 under 200ms") so you know when to stop.
3. Fix the biggest hotspot, in order of payoff: (a) algorithmic — O(n^2)→O(n log n) or a hashmap lookup beats any constant-factor tweak; (b) N+1 — batch into one query/call (`WHERE id IN (...)`); (c) caching/memoization for pure, hot, expensive work — WITH an invalidation story; (d) index DB columns you filter/join/sort on; (e) async/pool for IO; (f) stream/paginate large data instead of loading it all.
4. Re-measure after each change. Keep it if it moved the target; revert if it didn't (complexity has a cost).
5. Clean up loop discipline: hoist invariant work out of loops, build-then-join instead of string-concat, don't recompile regex / reopen connections per iteration.

## Pitfalls

- Optimizing code that isn't the bottleneck (the cardinal sin).
- Micro-optimizing in a slow path instead of fixing the algorithm or the SQL.
- Premature optimization that wrecks readability — correctness and clarity first.
- Caching with no invalidation (a stale cache is a bug, not a speedup).
- Claiming a speedup without before/after measurement.

## Verification

- You profiled, fixed the measured top hotspot, and re-measured a real improvement.
- The win is algorithmic/structural where possible, not a fragile micro-tweak.
- Any cache has a clear invalidation story; the simpler version was kept where data didn't justify more.
