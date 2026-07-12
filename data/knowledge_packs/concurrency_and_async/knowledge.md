# Concurrency & Async Reference

## Core distinctions
- **Concurrency** = tasks interleave progress (structure/composition); **parallelism** = executing literally at once on multiple cores (execution). Concurrency enables parallelism but doesn't require it.
- **IO-bound -> async / event loop** (waiting on net/disk/DB): one thread multiplexes thousands of sockets. **CPU-bound -> processes or real threads** (need cores). In GIL langs (CPython, Ruby MRI) threads don't parallelize CPU -> use `multiprocessing`/subinterpreters/native ext.
- **Thread** = shared address space, cheap switch, ~MB stack, race-prone. **Process** = isolated memory, IPC cost, crash-isolated. **Async task** = cooperative coroutine, ~KB, no preemption — a blocked coroutine that doesn't yield stalls everything.
- Preemptive (OS threads, can switch mid-instruction) vs cooperative (async, switches only at `await`). Cooperative = fewer races within a task but zero protection across `await` points.

## Shared state is the enemy
- Prefer **immutability**, **message-passing**, **channels/queues** over shared memory. "Don't communicate by sharing memory; share memory by communicating."
- If you must share: **confine** to one owner (thread ownership), pass **copies/immutable snapshots**, or **guard every access** with the same lock.
- **Memory model**: without synchronization, one thread's writes may be reordered/invisible to another (store buffers, caches, compiler reordering). Need **happens-before** edges — established by locks, atomics with proper ordering, thread join/start. Non-atomic/non-volatile shared reads = undefined/torn/stale.

## Races & atomicity
- **Read-modify-write is not atomic**: `count++` = load/add/store; two threads interleave -> lost update. Use an atomic or a lock.
- **TOCTOU** (`if not exists: create`): collapse check+act into one atomic op — `INSERT ... ON CONFLICT`, `SETNX`, compare-and-swap.
- **Atomics** (`AtomicInteger`, `std::atomic`, CAS) for single-word counters/flags/lock-free; **locks** for multi-field invariants. Atomics don't compose — two atomic ops ≠ one atomic transaction.
- Memory orderings: `seq_cst` (default, safe), `acquire`/`release` (pair to publish data), `relaxed` (counter only, no ordering). Get this wrong -> subtle, unreproducible bugs.

## Locks, mutexes, deadlock
- Hold locks **briefly**; **never do IO/blocking/callbacks under a lock** (invites deadlock + kills throughput).
- **Mutex** = mutual exclusion; **RWLock** = many readers XOR one writer (win only when reads >> writes; risks writer starvation); **spinlock** = busy-wait, only for ultra-short critical sections on multicore.
- **Reentrant/recursive** lock lets the holding thread re-acquire; non-reentrant self-deadlocks.
- **Deadlock — Coffman conditions** (all four needed): mutual exclusion, hold-and-wait, no preemption, circular wait. Break any one:
  - **Global lock ordering** — always `lock(A) then B`; kills circular wait. Primary tool.
  - **Try-lock + backoff/timeout**, acquire-all-or-release, or single coarse lock.
- **Livelock**: threads keep reacting, no progress (two people dodging in a hallway). **Starvation**: unfair scheduling; a thread never gets the lock.
- Prefer one coarse lock until profiling proves contention; then shard/fine-grain.

## Coordination primitives
- **Condition variable**: wait for a predicate; **always re-check in a `while` loop** (spurious wakeups); `notify_all` vs `notify_one`. Hold the lock while waiting/signaling.
- **Semaphore**: counting permits — bound concurrency (e.g. max N in-flight). Binary semaphore ≈ mutex but not owner-bound.
- **Barrier**: all N threads rendezvous before any proceeds. **Latch/`WaitGroup`**: wait for N tasks to finish.

## Async / await + event loops
- Event loop = single thread running a queue of ready callbacks/coroutines; `await` = yield control until awaitable resolves, then resume.
- **Never block the loop**: no `time.sleep`, sync DB/file/`requests` calls, or CPU-heavy loops — offload via `run_in_executor`/worker pool. One blocking call freezes all tasks.
- Independent awaits -> run together: `await gather(a(), b())` / `Promise.all([a(),b()])`. **Don't `await` in a loop** for independent work — it serializes; collect tasks, await once.
- Always **await/join** spawned work; **floating promises** swallow errors and leak. In JS, unhandled rejection crashes/warns; in asyncio, orphan tasks vanish.
- **Cancellation/timeouts**: every await/IO gets a deadline; propagate cancel tokens/`CancellationToken`/`asyncio.CancelledError`. **Structured concurrency** (nurseries, `TaskGroup`, `errgroup`): child tasks scoped to a block, auto-cancel siblings on error, no leaks.

## Concurrency models
- **Actors** (Erlang/Akka): isolated state + mailbox; process one message at a time -> no locks; supervision trees for fault recovery. Location-transparent; asynchronous, at-most-once/at-least-once delivery.
- **CSP / channels** (Go, `chan`): goroutines communicate over typed channels; `select` multiplexes. Unbuffered = rendezvous (sync handoff); buffered = queue. Close-to-signal-done; ranging over a channel drains it.
- **Fork-join / data parallelism**: split -> parallel map -> reduce (thread pools, `parallelStream`, SIMD, work-stealing deques). Load-balances via stealing from busy workers.
- **Futures/promises**: handle to a not-yet-computed value; compose with `then`/`map`/`await`. Eager (starts now, JS Promise) vs lazy (starts on poll/await, Rust futures). `Promise.all` (all), `race`/`any` (first) combinators.
- **Software transactional memory (STM)**: optimistic in-memory transactions, retry on conflict (Clojure `ref`, Haskell); composes better than locks, no manual ordering.

## Immutability & confinement
- **Immutable data** is inherently thread-safe — freely shareable, no locks. Favor `final`/`const`/frozen; return copies.
- **Copy-on-write**: readers share; a writer clones. Wins for read-mostly (config, snapshots).
- **Thread-local storage**: per-thread copy dodges sharing (but leaks in pooled threads — clear after use).
- **Confinement**: an object touched by exactly one thread needs no synchronization (thread-per-connection, single-writer principle).

## Async patterns
- **Fan-out/fan-in**: dispatch N tasks (`gather`/`Promise.all`), await all, combine. Bound N with a semaphore.
- **Worker pool over a queue**: fixed workers pull from a bounded channel; natural backpressure + concurrency cap.
- **Rate limiting / throttling**: token bucket or semaphore of N permits to cap in-flight or per-second calls.
- **Debounce/coalesce** bursty triggers; **single-flight** dedupes concurrent identical requests into one.

## Pools, producer-consumer, backpressure
- **Thread/worker pool**: bound concurrency; unbounded spawning = OOM, context-switch thrash, descriptor exhaustion. Size CPU pools ≈ cores; IO pools higher.
- **Producer-consumer**: bounded queue between stages decouples rates.
- **Backpressure**: bounded queues; when full, **block / drop / shed / reject** producers — never silently buffer. Unbounded queue = hidden memory leak + latency blowup that masks the real bottleneck.
- **Idempotency**: retries must be safe — dedupe keys, upserts, no double-charge (pairs with at-least-once delivery).

## Gotchas -> Fix
- **Data race on shared var** (torn/stale reads) -> guard with a lock or use an atomic; establish happens-before.
- **Deadlock from inconsistent lock order** -> impose one global lock ordering; or try-lock with timeout.
- **`await` in a loop** silently serializes throughput -> `gather`/`Promise.all` independent work.
- **Blocking call in async context** freezes every task -> offload to executor/thread pool; use async client libs.
- **Forgetting to join/await** -> lost results, swallowed errors, leaked tasks -> structured concurrency / always await.
- **Double-checked locking** is broken without a memory barrier -> use atomics/`volatile` or lazy-init idiom (`std::call_once`, static init).
- **Unbounded queue** hides backpressure -> OOM under load -> bound it and apply a shed/block policy.
- **CV wait without a loop** -> spurious wakeup acts on false predicate -> `while (!ready) cond.wait()`.
- **False sharing**: two threads write different vars on the **same cache line** -> cache-line ping-pong tanks perf -> pad/align hot per-thread data to 64B.
- **Priority inversion**: low-prio task holds a lock a high-prio task needs -> use priority inheritance or avoid shared locks across priorities.
- **Sharing a non-thread-safe object** (dict, `SimpleDateFormat`, non-reentrant lib) across threads -> confine per-thread (thread-local) or guard.
- **`async` fn never awaited** (JS) -> silent no-op; **`.then` without `.catch`** -> unhandled rejection.
- **GIL surprise**: threads for CPU work give no speedup in CPython -> use processes/native code.
- **Cancellation leaks**: timing out the caller but not the work -> pass and honor a cancel token; clean up in `finally`.
- **ABA problem** in lock-free CAS -> value reverts A->B->A, CAS wrongly succeeds -> use tagged pointers/hazard pointers/epoch reclamation.
