# Quantum Computing

## Mental model (read first)
- A quantum computer is **NOT** a classical parallel machine that "tries all answers at once." It holds a superposition, but **measurement returns one outcome** at random. Speedup comes from engineering **interference** so wrong answers' amplitudes cancel and the right answer's amplitude is amplified. No interference structure -> no advantage.
- Speedups are **problem-specific**: exponential (Shor factoring, simulating quantum systems), quadratic (Grover search), or none. Most problems get zero speedup.
- **Qubit** state: `|ψ⟩ = α|0⟩ + β|1⟩`, complex amplitudes, `|α|² + |β|² = 1`. Measuring gives `0` w.p. `|α|²`, `1` w.p. `|β|²`, then collapses.
- `n` qubits -> `2^n` complex amplitudes (state vector). This is the source of power AND why classical simulation is exponentially hard (~50 qubits is the classical wall).

## Qubits, Bloch sphere, measurement
- **Superposition**: qubit in a linear combination of basis states until measured. Not "both at once" in a usable readout sense.
- **Bloch sphere**: pure single-qubit state as a point on a unit sphere. `|0⟩` north pole, `|1⟩` south, equator = equal superpositions differing by **phase** (`|+⟩=(|0⟩+|1⟩)/√2`, `|−⟩`, `|+i⟩`…). Gates = rotations of this sphere.
- **Global phase** `e^{iθ}|ψ⟩` is unobservable; **relative phase** between amplitudes is physical and drives interference.
- **Measurement** is probabilistic + irreversible (collapse); in computational basis by default. Repeat the circuit many **shots** to estimate the output distribution.

## Gates & circuits
- Gates = **unitary** matrices (`U†U = I`) -> reversible, norm-preserving. All quantum operations except measurement are reversible.
- Single-qubit: **X** (NOT, bit flip), **Y**, **Z** (phase flip `|1⟩->−|1⟩`), **H** (Hadamard: creates superposition, `H|0⟩=|+⟩`), **S** (√Z, π/2 phase), **T** (π/4 phase), rotations `Rx(θ),Ry,Rz`.
- Two-qubit: **CNOT/CX** (flip target if control=1 — creates entanglement), **CZ**, **SWAP**. Three: **Toffoli/CCX** (reversible AND).
- **Universal gate sets**: `{H, T, CNOT}` or `{Clifford + T}` approximate any unitary. **Clifford gates alone are classically simulable** (Gottesman-Knill) — the non-Clifford **T gate** supplies quantum advantage.
- **Circuit**: qubits as wires (time L->R), gates applied in sequence, measurements at end. Depth = longest gate path; width = qubit count.

## Entanglement
- Correlations with no classical analog. **Bell state** `(|00⟩+|11⟩)/√2` via `H` on q0 then `CNOT(q0->q1)`: measuring one instantly determines the other (perfectly correlated), regardless of separation.
- Entangled state can't be written as a product of individual qubit states. Violates **Bell/CHSH inequalities** — no local hidden variables (Nobel 2022).
- Does **not** transmit information faster than light (outcomes are random until you compare via a classical channel). Basis for teleportation, superdense coding, many algorithms.

## Key algorithms
- **Deutsch-Jozsa**: determines if a black-box function is constant or balanced in **1 query** vs classical worst-case `2^{n-1}+1`. Pedagogical proof of exponential query separation via interference.
- **Grover's search**: unstructured search of `N` items in **O(√N)** (`~π/4·√N` iterations) vs classical O(N). Quadratic, not exponential; amplitude amplification. Overshooting iterations *lowers* success — count matters.
- **Shor's factoring**: factors integers in **polynomial** time (breaks RSA/ECC) — reduces factoring to period-finding solved by **Quantum Fourier Transform**. Needs many logical (error-corrected) qubits — not feasible on today's hardware.
- **Quantum simulation** (Feynman's original motivation): simulate molecules/materials — the clearest near-term exponential win. Also HHL (linear systems, caveated), QFT, phase estimation.

## No-cloning, decoherence, error correction
- **No-cloning theorem**: an unknown quantum state cannot be copied (`U|ψ⟩|0⟩=|ψ⟩|ψ⟩` is impossible for arbitrary `|ψ⟩`). -> no classical-style copy/backup; enables QKD security.
- **Decoherence**: environment entangles with qubits, destroying superposition. **T1** (energy relaxation), **T2** (dephasing) — coherence times ~µs–ms. Gate/readout errors ~0.1–1%.
- **Quantum error correction (QEC)**: spread 1 logical qubit over many physical qubits (**surface code** ~1000:1), measure **syndromes** without collapsing data, correct. Needs error rate below a **threshold** (~1%). **Fault tolerance** is the goal; we're not there at scale yet.

## NISQ + variational
- **NISQ** (Noisy Intermediate-Scale Quantum): 50–1000 noisy, non-corrected qubits — today's regime. Shallow circuits only (noise accumulates with depth).
- **Variational/hybrid** algorithms: parameterized quantum circuit (ansatz) + classical optimizer in a loop.
  - **VQE** (Variational Quantum Eigensolver): estimate ground-state energy of a Hamiltonian (chemistry). Minimize `⟨ψ(θ)|H|ψ(θ)⟩`.
  - **QAOA**: approximate combinatorial optimization (Max-Cut). Alternate cost/mixer layers.
  - Caveats: **barren plateaus** (vanishing gradients), noise, unclear advantage vs classical.
- Tools: **Qiskit** (IBM), **Cirq** (Google), **PennyLane** (differentiable/QML), **Q#**, **Braket** (AWS). Run on simulators or cloud QPUs; count shots.

## What it's good (and bad) for
- **Good**: simulating quantum chemistry/materials (exponential), factoring/discrete log (Shor -> crypto), unstructured search (Grover, quadratic), some optimization/sampling, quantum machine learning (unproven advantage).
- **Bad/no advantage**: general everyday computing, most business logic, arbitrary databases (Grover needs a quantum oracle, not a stored DB), problems without exploitable structure. It's a specialized coprocessor, not a faster CPU.
- **Quantum supremacy/advantage** demonstrations (Google 2019 Sycamore, USTC) solved contrived sampling tasks — not yet a useful application.

## Math & notation essentials
- **Dirac notation**: ket `|ψ⟩` = column vector, bra `⟨ψ|` = conjugate-transpose row. `⟨φ|ψ⟩` = inner product (overlap amplitude); `|φ⟩⟨ψ|` = outer product (operator).
- Basis: `|0⟩=[1,0]ᵀ`, `|1⟩=[0,1]ᵀ`. Multi-qubit via **tensor product** `⊗`: `|01⟩=|0⟩⊗|1⟩` (4-vector). Ordering convention matters (big-endian vs little-endian; Qiskit is little-endian — qubit 0 is the rightmost bit).
- Gate on a state = matrix-vector multiply. `X=[[0,1],[1,0]]`, `Z=[[1,0],[0,−1]]`, `H=(1/√2)[[1,1],[1,−1]]`. Sequential gates = matrix product (right-to-left of application order).
- Probability of outcome = `|amplitude|²` (Born rule); amplitudes sum in modulus-squared to 1. Expectation value `⟨ψ|O|ψ⟩` for observable `O`.
- **Density matrix** `ρ` describes mixed states (statistical ensembles) + open systems; pure state `ρ=|ψ⟩⟨ψ|`, `Tr(ρ)=1`. Needed for noise/decoherence modeling.

## Hardware & modalities
- Physical qubit types: **superconducting** transmons (IBM, Google — fast gates, mK dilution fridge), **trapped ions** (IonQ, Quantinuum — high fidelity, all-to-all, slower), **neutral atoms** (QuEra), **photonic** (Xanadu — room temp, hard 2-qubit), **spin/quantum dots**, **topological** (aspirational).
- Metrics: qubit count, gate fidelity (1q ~99.9%, 2q ~99%), coherence T1/T2, connectivity (limited -> need SWAP inserts), **Quantum Volume** (holistic), CLOPS (speed).
- **Transpilation/compilation**: map logical circuit to hardware's native gate set + connectivity (routing/SWAP insertion), optimize depth. Handled by Qiskit `transpile`.

## Workflow (Qiskit sketch)
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(2, 2)
qc.h(0); qc.cx(0, 1)      # Bell state
qc.measure([0,1], [0,1])   # -> ~50% '00', 50% '11'
```
- Loop: build circuit -> transpile to backend -> run with N shots -> read counts histogram -> post-process. Simulate first (Aer), then real QPU. Use **error mitigation** (readout calibration, zero-noise extrapolation) on NISQ hardware.

## Misconceptions -> Fix
- "Tries all answers simultaneously / massive parallelism" -> only one outcome on measurement -> think interference: amplify correct amplitude, cancel wrong ones.
- "More qubits = universally faster computer" -> only helps problems with quantum structure -> most tasks see no speedup; don't port classical code.
- "Measure to read the whole superposition" -> measurement collapses to one basis state -> repeat many shots to sample the distribution; you never see all amplitudes.
- "Entanglement sends signals faster than light" -> no, outcomes random without classical comparison -> no FTL communication.
- "Grover: run more iterations, better answer" -> success oscillates; overshoot fails -> use `~π/4·√N` iterations exactly.
- "Copy a qubit to back it up / eavesdrop" -> no-cloning forbids it -> use teleportation (consumes an entangled pair + classical bits; original destroyed).
- "Qubits are just probabilistic bits" -> amplitudes are complex with phase and interfere; probabilities don't -> the phase is the point.
- "Today's QPUs break RSA" -> Shor needs millions of physical error-corrected qubits; NISQ can't -> current threat is "harvest-now-decrypt-later," motivating post-quantum crypto now.
- "Simulate a quantum computer classically to get the speedup" -> state vector is `2^n`; ~50 qubits exhausts supercomputers -> no free classical lunch.
- "Deeper circuit = more powerful on real hardware" -> noise/decoherence ruin deep NISQ circuits -> keep circuits shallow, use error mitigation.
