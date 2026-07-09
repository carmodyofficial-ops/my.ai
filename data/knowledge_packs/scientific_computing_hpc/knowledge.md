# Scientific Computing & HPC

## Pick-the-tool cheat sheet
- Dense linear algebra: **BLAS** (vendor: MKL, OpenBLAS, cuBLAS) + **LAPACK** (solve/eig/SVD). Never hand-roll matrix multiply — call optimized BLAS (levels 1 vec, 2 mat-vec, 3 mat-mat; level-3 is cache-friendly, fastest).
- Sparse: **SuiteSparse**, **PETSc**, **Eigen**, `scipy.sparse` (CSR/CSC). Iterative solvers **CG** (SPD), **GMRES/BiCGStab** (nonsymmetric) + **preconditioner** (ILU, AMG).
- Parallel: **OpenMP** (shared memory, threads, `#pragma omp parallel for`), **MPI** (distributed, message passing), **CUDA/HIP** (GPU), hybrid MPI+OpenMP+GPU.
- Languages: **Fortran/C/C++** (compiled, BLAS-native), **Julia** (JIT, fast + high-level), **Python/NumPy** (glue; vectorize, offload to C/Fortran). **NumPy/SciPy**, **Numba/Cython** to speed hot loops.

## Floating point (IEEE 754)
- **double** (binary64): 1 sign + 11 exp + 52 mantissa, ~15–16 significant decimal digits, machine epsilon `ε ≈ 2.22e-16`. **float** (binary32) ~7 digits, `ε≈1.19e-7`. Half/bfloat16 for ML.
- Not all reals representable; **0.1 has no exact binary form**. Never test floats with `==` -> use `|a−b| <= atol + rtol*|b|`.
- **Catastrophic cancellation**: subtracting nearly equal numbers loses significant digits (e.g. `1−cos(x)` small x). Rewrite algebraically (`2sin²(x/2)`), use stable formulas (quadratic: avoid `−b+√…` when it cancels).
- Non-associative: `(a+b)+c != a+(b+c)` -> sum small-to-large or use **Kahan summation**; parallel reductions reorder -> results vary bit-for-bit.
- Special values: `Inf`, `NaN` (NaN != NaN, propagates), signed zero, subnormals (slow/flush-to-zero). Watch overflow/underflow.
- **Conditioning** (problem sensitivity, condition number `κ`) vs **stability** (algorithm's error growth). Ill-conditioned (`κ` large) amplifies input error regardless of algorithm. Backward-stable algorithm gives exact answer to a nearby problem.

## Numerical methods
- **Root finding**: Newton (quadratic convergence, needs derivative + good guess), bisection (robust, linear), secant, Brent (hybrid, default).
- **Linear systems**: LU (`Ax=b` general), Cholesky (SPD, 2x faster), QR (least squares), SVD (rank/pseudo-inverse). **Never invert a matrix to solve** — factor and back-substitute (faster, stabler).
- **Interpolation/quadrature**: splines; Gauss/Simpson/adaptive integration.
- **ODEs**: explicit **RK4** (nonstiff), adaptive (Dormand-Prince `ode45`/`RK45`). **Stiff** systems (widely separated timescales) need **implicit** solvers (backward Euler, BDF/`ode15s`, Rosenbrock) — explicit methods force tiny steps. CFL condition limits explicit time step in PDEs.
- **PDEs**: finite difference / finite element (FEM) / finite volume / spectral -> large sparse systems. Discretize space+time; check stability (von Neumann).
- **Monte Carlo**: sample randomly, error `~1/√N` (dimension-independent — beats grids in high-D). Variance reduction (importance/stratified/antithetic), QMC (Sobol) for smoother `~1/N`. Seed + record RNG for reproducibility.

## Parallelism
- **Shared memory (OpenMP)**: threads share address space; fork-join. Watch **data races** (use `reduction`, `atomic`, `critical`, private vars), false sharing (cache-line contention). Scales to one node's cores.
- **Distributed (MPI)**: separate processes/address spaces, explicit messages. `MPI_Send/Recv` (point-to-point), collectives `MPI_Bcast/Reduce/Allreduce/Scatter/Gather/Alltoall`. Scales across nodes. **Domain decomposition**: partition grid, exchange **halo/ghost cells** at boundaries each step; minimize surface/volume ratio.
- **Overlap communication with computation** (nonblocking `MPI_Isend/Irecv`) to hide latency.
- **GPU (CUDA)**: massive SIMT parallelism. Host/device separate memory -> transfers over PCIe are the bottleneck (minimize/overlap with streams). Threads -> warps (32) -> blocks -> grid. **Coalesce** global memory access; use **shared memory** for reuse; avoid warp **divergence** (branchy code serializes). Occupancy matters.
- **Vectorization/SIMD**: one instruction on a vector (SSE/AVX/AVX-512, NEON). Compiler auto-vectorizes tight, branch-free, unit-stride loops; help with alignment, `restrict`, `#pragma omp simd`. 4–16x on hot kernels.

## Profiling & scaling
- **Amdahl's law** (fixed problem, strong scaling): speedup `<= 1/(s + (1−s)/p)`; serial fraction `s` caps it (5% serial -> max 20x). **Gustafson**: grow problem with `p` (weak scaling) -> near-linear achievable.
- **Strong scaling**: fixed total size, more procs -> should drop runtime (limited by Amdahl + comm). **Weak scaling**: fixed size *per* proc, grow both -> tests communication overhead.
- **Roofline model**: perf bounded by compute (FLOP/s) or memory bandwidth vs **arithmetic intensity** (FLOP/byte). Most scientific kernels are **memory-bound**, not compute-bound.
- Profile before optimizing: `perf`, VTune, `nvprof/Nsight`, `gprof`, `nvidia-smi`, MPI profilers (Scalasca, TAU). Find the hot 3%.

## Language & library choices
- **Fortran**: still king for numerical kernels — column-major, native arrays, mature compilers, BLAS/LAPACK heritage. **C/C++**: control, Kokkos/RAJA for portability, Eigen for linear algebra.
- **Julia**: JIT (LLVM), near-C speed with high-level syntax, multiple dispatch, built-in arrays/BLAS, `@simd`/`@threads`/`Distributed`/CUDA.jl — good for new HPC-ish code.
- **Python/NumPy**: productivity glue. Speed comes from vectorized array ops calling C/Fortran BLAS; hot Python loops are slow -> vectorize, or use **Numba** (`@njit`), **Cython**, or offload (CuPy, JAX, Dask, mpi4py).
- Rule: never write scalar loops in interpreted languages for hot paths; express as array ops or drop to compiled kernels.

## Cluster & job execution
- **HPC cluster**: login nodes (don't compute here) + compute nodes + shared parallel filesystem (**Lustre/GPFS**) + fast interconnect (**InfiniBand**, low latency). Never run heavy jobs on login nodes.
- **Scheduler**: **SLURM** (`sbatch`, `srun`, `squeue`, `scancel`), PBS/Torque, LSF. Request nodes/tasks/cores/GPUs/walltime/memory; jobs queue by priority/fairshare. `#SBATCH` directives in the batch script; `mpirun`/`srun` launches ranks.
- **Module system** (`module load gcc openmpi`) manages compiler/library environments. Pin toolchain versions.
- Parallel I/O: many ranks writing many small files kills Lustre metadata -> use **MPI-IO**, **HDF5/NetCDF** (parallel), or aggregate writes; avoid per-rank files at scale.

## Performance engineering
- **Memory hierarchy**: registers -> L1/L2/L3 cache -> DRAM -> disk, each ~10x slower + bigger. Optimize for locality (temporal + spatial). Cache line ~64 bytes.
- **Arithmetic intensity** low -> memory-bound (most stencils, sparse matvec); high -> compute-bound (dense GEMM). Blocking/tiling raises reuse.
- **Data layout**: **SoA (struct-of-arrays)** vectorizes better than AoS; align to cache lines; pad to avoid false sharing.
- **NUMA**: multi-socket nodes have per-socket memory; **first-touch** allocation places pages near the touching thread -> initialize data in parallel the same way you use it; pin threads (`OMP_PROC_BIND`, `numactl`).
- Compiler: `-O2/-O3`, `-march=native`, `-funroll-loops`, report vectorization (`-fopt-info-vec`, `-qopt-report`). Link the right BLAS.

## Reproducibility
- Pin compiler + flags (`-O3 -march=native` changes results), BLAS version, MPI ranks, RNG seeds. Optimization/parallel reordering changes FP results bit-for-bit — reproducibility means "within tolerance," not identical.
- Containers (Singularity/Apptainer on clusters), Spack/EasyBuild for builds, module systems. Record environment + versions with outputs.

## Pitfalls -> Fix
- **`==` on floats / expecting exactness** -> spurious failures -> tolerance compare; know `ε`.
- **Catastrophic cancellation** -> lost precision -> reformulate the expression; use stable algorithms.
- **Inverting matrices** / solving via `inv(A)*b` -> slow + unstable -> LU/Cholesky solve.
- **Explicit solver on a stiff ODE** -> blows up or crawls -> use implicit/BDF; check CFL for PDEs.
- **Load imbalance** (uneven work per rank) -> fastest waits for slowest, idle cores -> dynamic scheduling / balanced partitioning / work stealing.
- **Communication overhead** dominates (too-fine decomposition, chatty small messages) -> aggregate messages, overlap comm/compute, minimize halo exchange, prefer collectives.
- **Memory-bound kernel treated as compute-bound** -> optimizing FLOPs uselessly -> improve locality/blocking, reduce data movement (roofline says so).
- **Cache misses / poor locality** (wrong loop order, column-major vs row-major mismatch) -> stalls -> loop tiling/blocking, traverse contiguous (Fortran col-major, C row-major), use BLAS-3.
- **Data races in OpenMP** (shared write) -> nondeterministic wrong results -> reduction/atomic/private; test with thread sanitizer.
- **Excess host<->device transfers (GPU)** -> PCIe bottleneck kills speedup -> keep data on device, batch transfers, overlap with streams.
- **Non-reproducible parallel sums** -> results drift across runs/ranks -> ordered/Kahan reduction if bitwise needed; else document tolerance.
- **`-ffast-math`/aggressive flags** silently break NaN handling & associativity -> unexpected wrong answers -> use cautiously, validate.
- **Heavy work on login node** -> admins kill it, degrades shared node -> submit via SLURM to compute nodes.
- **Per-rank file explosion on Lustre** -> metadata server overload -> parallel HDF5/MPI-IO, aggregate output.
- **NUMA-blind allocation** (init serially, use in parallel) -> remote memory access, poor scaling -> first-touch init in parallel, pin threads.
- **AoS layout blocking vectorization** -> scalar fallback -> restructure to SoA, align, ensure unit stride.
- **Ignoring `κ` (conditioning)** -> trusting a precise-looking but meaningless answer -> estimate condition number; regularize/refine (iterative refinement) for ill-conditioned systems.
- **Global `MPI_Barrier`/synchronization overuse** -> serialization -> remove unnecessary barriers, use nonblocking collectives.
