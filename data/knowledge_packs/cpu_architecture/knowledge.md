# CPU Architecture

## Organization
- Von Neumann: unified memory for code + data (single bus → von Neumann bottleneck). Harvard: separate instruction/data memories/buses; modern CPUs are "modified Harvard" (split L1I/L1D caches, unified lower levels).
- Core blocks: fetch, decode, register file, ALU/FPU, load-store unit, control. ISA (RISC — fixed-width, load-store, many regs; CISC — variable-width, mem operands; x86 decodes CISC→RISC-like μops internally).

## Instruction Cycle
- Classic RISC stages: IF (fetch from I-cache using PC) → ID (decode, read registers) → EX (ALU/branch resolve) → MEM (load/store D-cache) → WB (write result to register).
- PC advances sequentially unless branch/jump/interrupt redirects. μop decode on x86; μop cache skips re-decode of hot loops.

## Pipelining & Hazards
- Overlap stages so ~1 instruction completes/cycle (IPC target). Depth trades latency for clock frequency; deeper pipe = costlier flush.
- Structural hazard: two instructions need same resource same cycle -> duplicate/pipeline the unit (e.g., separate I/D cache ports).
- Data hazard: instruction needs a not-yet-written result. RAW (true dependency). Handle by forwarding/bypassing (route ALU output directly to next EX) — eliminates most stalls; load-use hazard still needs 1 stall (load result not ready until MEM). WAR/WAW are false deps removed by register renaming.
- Control hazard: branch outcome unknown at fetch -> stall or speculate; misprediction flushes speculated instructions (penalty ∝ pipeline depth).

## Branch Prediction & Speculation
- Predict direction (taken/not) and target early to keep fetch fed. Static (backward-taken/forward-not) vs dynamic.
- Dynamic: 2-bit saturating counters (per-branch history), 2-level/gshare (global history XOR PC), TAGE (multiple history lengths — SOTA), loop predictors. BTB caches targets; RAS (return-address stack) predicts returns; indirect-branch predictors for vtables/switch.
- Speculative execution runs down predicted path; results held speculative, committed in order or squashed. Basis of Spectre/Meltdown side channels (speculative loads leave cache traces).

## Superscalar & Out-of-Order
- Superscalar: multiple execution ports issue >1 instruction/cycle (IPC>1). Wide decode/issue.
- OOO (Tomasulo-style): fetch/decode/retire in order; execute out of order as operands ready. Register renaming (map arch regs → larger physical reg file) removes WAR/WAW. Reservation stations / scheduler hold waiting μops; ROB (reorder buffer) tracks in-order retirement + precise exceptions; results committed in program order.
- ILP: independent instructions the HW can overlap. Limited by true deps, branch predictability, memory latency, and machine width. Load/store queue enables memory disambiguation + store-to-load forwarding.

## Cache Hierarchy
- Latency ladder (approx cycles): register ~0, L1 ~4, L2 ~12, L3 ~40, DRAM ~200+. Caches exploit temporal + spatial locality.
- Line = transfer/coherence unit (typically 64 bytes). A miss fetches whole line → nearby data comes "free".
- Associativity: direct-mapped (1 way — conflict misses), N-way set-associative, fully associative. Index selects set, tag identifies line within set; replacement (LRU/pseudo-LRU/random) within set.
- Miss taxonomy (3 C's): compulsory (cold/first touch), capacity (working set > cache), conflict (set pressure). Prefetchers (stride/stream) hide compulsory/capacity misses.
- Write policy: write-back (dirty bit, defer store to memory — less bandwidth) vs write-through; write-allocate vs no-write-allocate. TLB is a cache for page translations (see VM).

## Coherence & Memory Model
- Multi-core: each core's private cache must stay coherent. MESI: line states Modified (dirty, exclusive), Exclusive (clean, only owner), Shared (clean, multiple), Invalid. Writes require Exclusive/Modified → invalidate other copies (RFO, request-for-ownership). MOESI/MESIF add Owned/Forward to share dirty data / cut memory traffic. Snooping (bus) vs directory-based (scalable).
- Memory ordering: x86 = TSO (Total Store Order — loads not reordered after loads, stores not after stores; store→load can reorder via store buffer). ARM/POWER = weakly ordered (aggressive reordering).
- Barriers/fences enforce ordering: `mfence`/`lfence`/`sfence` (x86), `dmb`/`dsb` (ARM); acquire/release semantics for locks. Store buffer + invalidate queue are why fences are needed. Atomics (`lock`-prefixed / LL-SC) provide RMW + ordering.

## Performance Counters & Measurement
- PMU exposes hardware events (cycles, instructions, cache-misses at each level, branch-misses, stalled-cycles, LLC-load-misses). `perf stat`/`perf record`, VTune, `toplev` (top-down microarchitecture analysis: attribute cycles to Frontend-Bound / Backend-Bound [Core vs Memory] / Bad-Speculation / Retiring).
- Key derived metrics: IPC (instructions/cycle — machine width caps it), MPKI (misses per 1000 instructions), branch-misprediction rate. Measure before optimizing; intuition about hotspots is often wrong.

## SIMD & Data Parallelism
- Single Instruction Multiple Data: one op on vector of lanes. x86 SSE(128b)/AVX(256b)/AVX-512(512b), ARM NEON/SVE. Speeds up dense array/DSP/ML kernels.
- Requires data-level parallelism, alignment for best throughput, and structure-of-arrays layout. Autovectorization by compiler or intrinsics/hand asm. Predication/masking for conditional lanes.

## Registers vs Memory
- Register file: fastest, tiny (dozens of arch regs, larger physical pool for renaming). Keep hot values in regs; spilling to stack costs loads/stores.
- Memory-bound code (low arithmetic intensity, FLOP/byte) is limited by bandwidth, not compute (roofline model) — no ILP or wider ALUs help.

## Multicore, SMT & Interconnect
- SMT/Hyper-Threading: 2+ arch thread contexts share one core's execution resources → hide stalls (memory latency) by running the other thread; contends for caches/ports, so gains are workload-dependent (can hurt cache-bound code).
- Chip topology: cores + private L1/L2, shared L3 (often sliced with a ring/mesh interconnect); multi-socket NUMA (local vs remote DRAM latency/bandwidth asymmetry). Cross-core communication cost dominated by cache-line ping-pong over the interconnect.
- Frequency scaling (DVFS), turbo boost, thermal/power limits (TDP) mean sustained clock < peak; AVX-512 can down-clock the core.

## Instruction Latency vs Throughput
- Each μop has latency (cycles until result usable) and throughput (issues per cycle across ports). Independent ops pipeline at throughput rate; dependent chains pay full latency. Divide/sqrt and cross-lane shuffles are high-latency, low-throughput.
- Micro-op fusion (cmp+jcc) and macro-op fusion reduce μop count. Loop stream detector / μop cache feed hot loops without re-decode.

## Virtual Memory Interaction
- Every memory access is virtual → TLB translation on the critical path; L1 is often VIPT (virtually-indexed, physically-tagged) so TLB lookup overlaps cache index. TLB miss triggers a page-table walk (hundreds of cycles) — page-walk caches mitigate.

## Security Side Effects
- Speculation/OOO leak microarchitectural state: Spectre (bounds-check/branch-target mistraining → speculative access, exfiltrated via cache timing), Meltdown (speculative read across privilege before fault retires). Mitigations: retpolines, barriers (`lfence`), KPTI page-table isolation, microcode — each costs performance. Timing side channels are why "constant-time" crypto avoids data-dependent branches/memory access.

## Gotchas -> Fix
- Cache misses from pointer-chasing / poor locality -> use contiguous arrays, block/tile loops, SoA layout, prefetch; improve access pattern before micro-tuning.
- False sharing: threads write distinct vars sharing one 64B line → constant invalidations -> pad/align per-thread data to a cache line (`alignas(64)`); separate hot read/write fields.
- Branch mispredict on unpredictable data-dependent branches -> make code branchless (conditional-move, masks, table lookup), or sort data to make branches predictable.
- Memory-bound kernel where more threads/FLOPs don't help -> raise arithmetic intensity (fusion, reuse in cache), reduce data movement; compare against roofline.
- Assuming multithreaded code is sequentially consistent -> use atomics with correct acquire/release ordering; insert barriers; don't rely on volatile for cross-thread sync.
- Unaligned/misaligned loads causing split-line or fault penalties -> align hot data; use aligned SIMD loads once alignment guaranteed.
- Denormal/subnormal floats trapping to slow microcode -> enable flush-to-zero/DAZ where precision allows.
- Long dependency chain serializes OOO engine (low ILP) -> break chains (multiple accumulators in reductions), unroll to expose independent ops.
- 4K aliasing / store-forwarding stalls (load overlaps recent store partially) -> avoid partial overlaps; match load/store sizes.
- Ignoring NUMA (remote-node memory latency) -> pin threads and allocate memory node-local (first-touch); avoid cross-socket sharing.
- TLB thrashing on large sparse working sets -> use huge pages to cut translation misses.
- Frontend-bound stalls (I-cache/μop-cache misses, decode limits from huge hot code) -> reduce code footprint, avoid excessive inlining, align loop heads.
- Under-utilizing SIMD width because compiler won't vectorize (aliasing/branches) -> annotate `restrict`, remove loop-carried deps, use `#pragma omp simd` or intrinsics.
- Contended atomic / lock on one cache line across cores -> shard counters per core and aggregate, or use relaxed atomics where ordering isn't needed.
