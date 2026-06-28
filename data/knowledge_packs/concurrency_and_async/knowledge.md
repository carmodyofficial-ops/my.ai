# Concurrency & Async Reference

## Core
- **Concurrency** = tasks make progress interleaved; **parallelism** = running literally at once. Concurrency is structure, parallelism is execution.
- **IO-bound -> async/event-loop** (waiting on net/disk). **CPU-bound -> threads/processes** (real cores; in GIL langs use processes).

## Shared State Is The Enemy
- Prefer **immutability**, **message-passing**, **channels/queues** over shared memory.
- If you must share: confine to one owner, pass copies, or guard every access.

## Locks / Mutexes
- Hold **briefly**; never do IO/blocking under a lock.
- **Consistent global lock order** everywhere -> prevents deadlock. `lock(A) then B` always.
- Prefer one coarse lock over many fine ones until profiling proves otherwise.

## Races & Atomicity
- **Read-modify-write is not atomic**: `count++` = load/add/store. Use atomics or a lock.
- `if not exists: create` (**TOCTOU**) — collapse check+act into one atomic op (`INSERT ... ON CONFLICT`, `setnx`).
- Atomics for single-word counters/flags; locks for multi-field invariants.

## Async/Await
- **Never block the event loop**: no `time.sleep`, no sync DB/file calls, no CPU loops — offload to a thread/process pool.
- Independent awaits -> run together:
  ```
  await gather(a(), b())   // Promise.all([a(),b()])
  ```
  **Don't `await` in a loop** for independent work — it serializes. Collect tasks, await once.
- Always **await/join** spawned work; floating promises swallow errors.

## Pools, Backpressure, Retries
- **Thread pool / worker queue**: bound concurrency; unbounded spawning = OOM/thrash.
- **Backpressure**: bounded queues; block/drop producers when full.
- **Idempotency**: retries must be safe — dedupe keys, upserts, no double-charge.
- **Cancellation/timeouts**: every await/IO gets a deadline; propagate cancel tokens.

## Gotchas
- Data race on shared var -> torn/stale reads.
- Deadlock from inconsistent lock ordering.
- `await`-in-loop silently serializes throughput.
- Blocking call in async ctx freezes all tasks.
- Forgetting to join/await -> lost results & errors.
- **Double-checked locking** is broken without proper memory barriers/atomics.
