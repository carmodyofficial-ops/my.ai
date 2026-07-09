# Node.js Internals & Performance

## Event loop phases (libuv)
- Phases per tick, in order: **timers** (`setTimeout`/`setInterval` callbacks whose threshold elapsed) → **pending callbacks** (deferred I/O errors, e.g. some TCP ECONNREFUSED) → **idle/prepare** (internal) → **poll** (retrieve new I/O events, execute I/O callbacks; blocks here waiting for I/O, bounded by nearest timer) → **check** (`setImmediate` callbacks) → **close** (`close` events, e.g. `socket.on('close')`).
- Between EACH phase (and after each callback) the **microtask queues** drain fully: `process.nextTick` queue first, then the Promise (`then`/`await`) microtask queue. This is why a recursive `nextTick`/promise chain can **starve** the event loop (I/O/timers never run).
- `process.nextTick` fires before Promise microtasks and before the loop continues → higher priority than `Promise.resolve().then`. Overusing `nextTick` for heavy work blocks I/O.
- `setImmediate` vs `setTimeout(fn,0)`: inside an I/O callback, `setImmediate` always runs first (check phase comes right after poll); at top level the order is non-deterministic (depends on loop start timing). `setImmediate` = "run after current poll phase".

## libuv threadpool
- Default 4 threads (`UV_THREADPOOL_SIZE`, max 1024, must set before first use). Used by: `fs` (most async file ops), `dns.lookup` (getaddrinfo, NOT `dns.resolve` which is async network), `crypto` (`pbkdf2`, `randomBytes`, `scrypt`), `zlib`. Network sockets use the OS async (epoll/kqueue), NOT the pool.
- Pool exhaustion: 5 concurrent slow `crypto.pbkdf2`/`fs` ops with default 4 threads → the 5th queues → tail latency. Bump `UV_THREADPOOL_SIZE` for fs/crypto-heavy workloads; it does NOT help pure network concurrency.

## Streams & backpressure
- `write()` returns `false` when internal buffer exceeds `highWaterMark` (default 16KB for byte streams, 16 objects in objectMode). Ignoring the `false` → unbounded buffering → memory blowup. Wait for `'drain'` before writing more.
- **Backpressure**: `readable.pipe(writable)` (and `pipeline`) handle it automatically — pause the source when the sink is full, resume on drain. Prefer `stream.pipeline(a,b,c,cb)` / `pipeline` from `stream/promises` over `.pipe()`: `.pipe()` does NOT forward errors or destroy the source on downstream failure → leaks/hangs. `pipeline` destroys all streams on error and calls back.
- `highWaterMark` is a threshold, not a hard cap; a single large chunk can exceed it. objectMode counts objects not bytes.
- Async iteration `for await (const chunk of readable)` respects backpressure and auto-destroys on break/throw. `Readable.from(asyncGenerator)` to build streams.
- Transform streams: implement `_transform`/`_flush`; watch that you don't buffer the whole input.

## worker_threads vs cluster vs child_process
- **CPU-bound** (parsing, crypto, image/ML, big JSON) → `worker_threads`: real threads in one process, share memory via `SharedArrayBuffer`/`Transferable` (`postMessage` transfer list avoids copy), low spawn cost. Use a **worker pool** (e.g. `piscina`); don't spawn per task.
- **Scale across cores for I/O/HTTP** → `cluster`: forks N processes sharing a listening socket (kernel/round-robin load balances). Each has its own event loop + memory. Good for stateless servers; no shared JS memory.
- **Run other programs / isolate** → `child_process` (`spawn` streams stdio, `exec` buffers output — beware `maxBuffer`, `fork` for Node children with an IPC channel). `exec` with unsanitized input = shell injection; prefer `execFile`/`spawn` with arg arrays.
- Rule: offload CPU to workers; scale I/O with cluster/multiple instances; workers do NOT help a purely I/O-bound event loop (it wasn't blocked).

## GC & memory
- V8 generational GC: **new space** (Scavenge, fast, small ~1–8MB semispaces) for short-lived objects; survivors promoted to **old space** (Mark-Sweep-Compact, can pause). Default old-space cap ~2GB (64-bit, older) / higher on modern; raise with `--max-old-space-size=4096` (MB). `--max-semi-space-size` tunes young-gen (bigger = fewer scavenges, more RSS).
- OOM: "JavaScript heap out of memory" → real leak or genuinely large working set. Take heap snapshots (`--inspect` + DevTools Memory, or `v8.writeHeapSnapshot()`), compare 3 snapshots, inspect Retainers for what pins growth. Common leaks: unbounded `Map`/cache (use LRU/`WeakMap`), event-emitter listeners not removed (`MaxListenersExceededWarning`), closures over big buffers, module-level arrays, global caches.
- `--expose-gc` + `global.gc()` for testing only. Monitor with `process.memoryUsage()` (`rss`, `heapUsed`, `external`, `arrayBuffers`) and `perf_hooks` gc observer.

## Profiling
- `node --prof app.js` → V8 tick log → `node --prof-process isolate-*.log` for a text profile (ticks by function, GC, C++). `--cpu-prof` writes a `.cpuprofile` loadable in DevTools flame chart.
- **clinic.js**: `clinic doctor` (diagnoses event-loop delay / GC / I/O), `clinic flame` (flamegraph of on-CPU time), `clinic bubbleprof` (async ops). `0x` for standalone flamegraphs.
- Event-loop lag = health signal: `perf_hooks.monitorEventLoopDelay()` histogram, or measure drift of a `setInterval`. High lag ⇒ CPU work blocking the loop.
- Flamegraph: wide frame = much on-CPU time; look for a fat plateau = hot function to optimize; tall = deep call stacks.

## async_hooks / AsyncLocalStorage
- `AsyncLocalStorage` provides continuation-local storage: `als.run(store, cb)` then `als.getStore()` anywhere in the async chain — request-scoped context (trace IDs, tenant, user) without threading params. Survives `await`/callbacks/timers.
- Cost: async_hooks tracking has overhead; `AsyncLocalStorage` is optimized but still non-zero. Don't store huge objects; beware context loss across some native/callback boundaries and older libs that break the async chain.

## Blocking & error handling
- Never block the loop: no `fs.readFileSync`/`crypto.*Sync`/big `JSON.parse`/synchronous loops in request path — every connection stalls. Chunk CPU work with `setImmediate`, offload to workers, or stream. `JSON.parse` of a huge string is synchronous and blocks.
- `unhandledRejection`: process emits it; since Node 15 default is to **crash** (exit non-zero). Attach `process.on('unhandledRejection')` for logging/graceful shutdown; don't swallow. `uncaughtException` means unknown state — log, run cleanup, then exit; do NOT resume serving.
- **Domains are deprecated/dead** — do not use for error handling; use `AsyncLocalStorage` for context and proper `try/catch`/`.catch()`/`pipeline` callbacks for errors.
- EventEmitter `'error'` with no listener throws and crashes the process — always attach an `error` handler on streams/sockets/emitters.

## Gotchas -> Fix
- Recursive `process.nextTick`/promise loop → event loop starved, timers/I/O never fire → **use `setImmediate` to yield to the loop**.
- Ignoring `write()===false` → unbounded buffer, RSS climbs → **await `'drain'` or use `pipeline`**.
- `.pipe()` on a failing stream → source not destroyed, fd/memory leak, hang → **use `stream.pipeline` (forwards errors, destroys all)**.
- 5+ concurrent `crypto.pbkdf2`/`fs` with default pool → mysterious latency spikes → **raise `UV_THREADPOOL_SIZE` (before first async op)**.
- `worker_threads` used to speed up an I/O-bound server → no gain → **workers help CPU-bound only; use cluster/instances for I/O scaling**.
- `child_process.exec(userInput)` → shell injection + `maxBuffer` truncation → **`execFile`/`spawn` with arg array; stream stdout**.
- `dns.lookup` under load blocks threadpool (getaddrinfo) → tail latency → **use `dns.resolve*` (async network) or raise pool size**.
- `setTimeout(fn,0)` assumed to run before `setImmediate` → order is non-deterministic at top level → **inside I/O callbacks use `setImmediate` for deterministic post-poll**.
- Unbounded `Map` cache → old-space growth → OOM → **LRU with cap, or `WeakMap`; monitor `heapUsed`**.
- Missing stream/emitter `'error'` listener → uncaught throw crashes process → **always attach `error` handlers**.
- `unhandledRejection` now crashes by default → silent in old code, fatal after upgrade → **handle every promise; add a process-level handler for graceful shutdown**.
- Using `domain` for error isolation → deprecated, leaks, unreliable → **remove; use try/catch + AsyncLocalStorage + pipeline**.
- Big synchronous `JSON.parse`/`readFileSync` in handler → blocks all requests → **stream/chunk or move to worker**.
- Raising `--max-old-space-size` to hide a leak → delays OOM, doesn't fix → **snapshot + fix the retainer**.
- `AsyncLocalStorage` context lost after a callback-based lib → **promisify or ensure the lib preserves async context; re-run `als.run` at the boundary**.
