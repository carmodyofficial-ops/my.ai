# Operating Systems Internals

## Processes vs Threads
- Process = address space + resources (open FDs, PID, page tables, signal handlers) + ≥1 thread. Isolated virtual memory; crash contained.
- Thread = schedulable execution context: own stack, registers, PC, TLS; shares heap/code/FDs with process peers.
- PCB (process control block / `task_struct` in Linux): PID, state, saved registers, page-table base (CR3), FD table, scheduling priority, signal state, parent/children links.
- `fork()` = duplicate process via copy-on-write pages; `exec()` = replace image; `clone()` (Linux) with flags implements both threads and processes (`CLONE_VM|CLONE_FILES|...`).
- Thread models: 1:1 (kernel thread per user thread — Linux/Windows), N:1 (user-level, no true parallelism), M:N (rare, complex).
- States: NEW → READY ↔ RUNNING → WAITING/BLOCKED → TERMINATED. Zombie = exited but parent hasn't `wait()`ed (reaps exit status); orphan = parent died, reparented to init/pid 1.

## Context Switching
- Save current registers/PC/PSW to PCB, switch page-table base register (flushes/tags TLB), restore next thread's state. Triggered by timer interrupt (preemption), blocking syscall, or yield.
- Cost: hundreds of ns to microseconds — direct (register save/restore) + indirect (cold TLB, cold caches, pipeline flush). Thread switch within same process is cheaper (no address-space/CR3 change → no full TLB flush; ASIDs/PCIDs avoid flush across processes).
- Mode switch (user↔kernel via syscall) is NOT a context switch — same process, ring change only.

## CPU Scheduling
- Goals trade off: throughput, latency/response time, fairness, CPU utilization, turnaround. No single optimum.
- FCFS: convoy effect (short jobs stuck behind long). SJF/SRTF: optimal average wait but needs burst prediction, starves long jobs.
- Round-robin: fixed time quantum; small quantum → responsive but more context-switch overhead; large → degenerates to FCFS.
- Priority scheduling: run highest priority; starvation risk → aging (raise priority over wait time). Preemptive vs non-preemptive.
- MLFQ (multilevel feedback queue): multiple RR queues by priority; jobs demoted on quantum exhaustion, promoted when I/O-bound; approximates SJF without prediction.
- Linux CFS: red-black tree keyed by `vruntime` (virtual runtime, weighted by nice); picks smallest vruntime → fair share. No fixed timeslice; targeted latency divided by weight. (EEVDF replaces CFS in newer kernels — deadline-based fairness.)
- Real-time: rate-monotonic (static, shorter period = higher priority) and EDF (dynamic, earliest deadline first, schedulable to 100% util).

## Virtual Memory
- Each process sees contiguous virtual address space; MMU translates VA→PA per access using page tables. Enables isolation, over-commit, sharing.
- Paging: fixed-size pages (4KB typical; 2MB/1GB huge pages). Multi-level page tables (x86-64: 4 levels PML4→PDPT→PD→PT, or 5-level) sparse-populate translations.
- TLB caches recent VA→PA translations; miss → page-table walk (HW on x86, SW-assisted elsewhere). TLB flush on address-space switch unless tagged (ASID/PCID).
- Page fault: minor (page in memory, just needs mapping/COW resolve), major (must read from disk/swap), invalid (segfault/SIGSEGV). Handler updates page table, resumes faulting instruction.
- Demand paging: pages loaded lazily on first access. Copy-on-write: fork shares pages read-only, duplicates on write fault.
- Replacement: LRU (approx via clock/second-chance using reference bit), FIFO (suffers Belady's anomaly), working-set model. Dirty pages must be written back before eviction.
- Swapping/paging to disk under memory pressure; `mmap` maps files/anon memory into VA space.

## Memory Allocation
- Kernel: buddy allocator (power-of-2 blocks, splits/coalesces to fight external fragmentation) + slab/slub allocator (caches for fixed-size objects, avoids fragmentation, fast reuse).
- User heap: `brk`/`sbrk` and `mmap`; allocators (ptmalloc/glibc, jemalloc, tcmalloc) use size-class bins, arenas per-thread to reduce lock contention.
- Fragmentation: external (free gaps too small) vs internal (rounding up to allocation granularity).

## Synchronization
- Race condition: outcome depends on unsynchronized interleaving of shared-state access. Critical section = code needing mutual exclusion.
- Mutex: ownership, sleeps on contention. Spinlock: busy-waits, only for very short critical sections / interrupt context (never hold while sleeping). Semaphore: counter, `wait`/`signal` (P/V); binary ≈ mutex but no ownership. Monitor/condition variable: mutex + wait/signal on predicates (`while(!cond) wait()` — always re-check under loop for spurious wakeups).
- Atomics + memory barriers underpin lock-free structures; CAS (compare-and-swap) primitive.
- Deadlock — Coffman conditions (all four required): mutual exclusion, hold-and-wait, no preemption, circular wait. Break any one to prevent (e.g., global lock ordering kills circular wait). Detect via wait-for graph cycle; recover by kill/rollback. Avoidance: Banker's algorithm.
- Livelock (threads active but no progress), starvation (unfair scheduling), priority inversion.

## System Calls & Protection
- CPU rings: user mode (ring 3) restricted; kernel mode (ring 0) full privilege. Syscall = controlled entry via trap/`syscall`/`sysenter` instruction → switches to kernel stack, runs handler by syscall number, returns.
- libc wraps syscalls; `errno` conveys failure. vDSO maps read-only kernel data (e.g. `gettimeofday`) to avoid trap cost.
- Traps (synchronous, from instruction), interrupts (async, from device), exceptions (faults/aborts).

## File Systems
- Inode: file metadata (mode, owner, size, timestamps, link count, block pointers — direct + single/double/triple indirect). Directory = map name→inode number. Hard link = extra name to same inode; symlink = path pointer.
- Layout: superblock (FS params), inode table, data blocks, free-space bitmap/extent tree.
- Journaling (ext4/XFS/NTFS): write intent to journal before applying → crash-consistent replay. Modes: writeback, ordered (data before metadata commit — default), data=journal (full). Avoids lengthy fsck.
- Copy-on-write FS (ZFS/Btrfs): never overwrite in place → atomic snapshots, checksums.
- Page cache buffers file data; writeback flushes dirty pages; `fsync` forces durability. VFS abstracts FS types behind common interface.

## I/O
- Programmed I/O (polling) wastes CPU; interrupt-driven notifies on completion; DMA transfers bulk data device↔memory without CPU, raises single completion interrupt.
- Interrupt handling: top half (fast, acks HW) + bottom half (deferred work — softirq/tasklet/workqueue). Interrupt coalescing reduces rate at high throughput. IRQ vectors dispatched via IDT; MSI/MSI-X deliver per-queue interrupts for multiqueue NICs/NVMe.
- Block vs character devices; I/O schedulers (mq-deadline, BFQ) reorder for fairness/latency.
- Blocking vs non-blocking vs async I/O; readiness (`select`/`poll`/`epoll`/`kqueue` — O(1) epoll vs O(n) select) vs completion models (`io_uring`, Windows IOCP). `epoll` edge- vs level-triggered: edge fires once per transition → must drain the FD fully or stall.
- Memory-mapped I/O maps device registers into physical address space; port-mapped I/O uses `in`/`out` on a separate address space.

## Kernel Architectures
- Monolithic (Linux): drivers/FS/net in kernel space — fast (no message-passing), large TCB. Microkernel (QNX/seL4/Mach): minimal kernel (IPC, scheduling, memory), services in user space — isolation/reliability at IPC cost. Hybrid (Windows NT, XNU). Loadable kernel modules extend monolithic kernels at runtime.
- Preemptible kernel: high-prio task can preempt kernel-mode execution → lower latency; non-preemptible sections guarded by disabling preemption/interrupts.
- Timers: periodic tick vs tickless (NO_HZ) to save power; high-resolution timers via hrtimers.

## IPC
- Pipes: unidirectional byte stream, anonymous (related procs) or named (FIFO). Bounded buffer → writer blocks when full.
- Shared memory (`shm`/`mmap`): fastest, requires own synchronization (semaphores).
- Message queues, Unix domain sockets (bidirectional, can pass FDs via `SCM_RIGHTS`).
- Signals: async notification (SIGKILL/SIGSEGV/SIGCHLD); handler must be async-signal-safe; SIGKILL/SIGSTOP uncatchable.

## Gotchas -> Fix
- Race on shared counter -> guard with mutex/atomic; never assume `++` is atomic.
- Deadlock from inconsistent lock order -> impose and document a global lock hierarchy; acquire in one order everywhere.
- CV wakeup without re-checking predicate -> always `while(!cond) wait()`, never `if` (spurious/stolen wakeups).
- Holding a spinlock across a blocking call/sleep -> use a mutex, or shorten critical section; spinlocks are for non-sleeping short sections only.
- Thrashing (constant paging, ~0 useful work) -> reduce working set / degree of multiprogramming; add RAM; working-set-aware admission.
- Priority inversion (low-prio holds lock high-prio needs, mid-prio preempts) -> priority inheritance or priority ceiling protocol.
- Zombie accumulation -> reap with `wait`/`waitpid` or `SIG_IGN` on SIGCHLD.
- fork() in multithreaded process -> child has only the calling thread; locks held by others frozen — call only async-signal-safe funcs before `exec`.
- TOCTOU (check-then-use on filesystem) -> use `openat`/fd-relative ops and O_NOFOLLOW; operate on the fd, not the re-resolved path.
- Assuming write() = durable -> data sits in page cache; call `fsync` (and fsync the directory for renames) for crash durability.
- False sharing of unrelated vars in one cache line -> pad/align hot per-thread data to cache-line boundaries.
- Ignoring EINTR on syscalls -> retry interrupted syscalls or use SA_RESTART.
