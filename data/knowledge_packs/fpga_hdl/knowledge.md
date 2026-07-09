# FPGA & HDL (Verilog / VHDL)

## Mental model — hardware, not software
- HDL **describes hardware**, it does not execute line-by-line. Everything you write becomes **gates, wires, flip-flops** running **concurrently**, in parallel, all the time.
- Order of concurrent statements/`always` blocks is irrelevant — they all "run" simultaneously. Loops (`for` in synthesizable code) **unroll** into replicated hardware, not iterations over time.
- You are **inferring** structure: an assignment to a register on a clock edge -> a flip-flop; a combinational expression -> LUTs/gates. Synthesis maps this to the FPGA's LUTs, FFs, BRAM, DSP blocks.
- FPGA = sea of configurable logic blocks (LUT+FF), routing fabric, block RAM, DSP slices, clock/PLL resources, I/O banks. Bitstream configures it.

## Combinational vs sequential
- **Combinational**: output = pure function of current inputs, no memory. Verilog `always @(*)` with **blocking** `=`, or `assign`. Must assign the output in every path (else latch inferred).
- **Sequential**: state updated on a clock edge -> flip-flops/registers hold value between clocks. `always @(posedge clk)` with **non-blocking** `<=`.
- **Golden rule (Verilog)**: use non-blocking `<=` in clocked/sequential blocks; use blocking `=` in combinational blocks. Never mix the two in one block.
  - Blocking `=` executes immediately, in order (like software) — models combinational chains.
  - Non-blocking `<=` schedules the RHS, all update together at end of the time step — models parallel registers correctly (avoids race, matches real FF behavior).

## Verilog basics
```verilog
module counter(input clk, rst_n, input en, output reg [7:0] q);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)      q <= 8'd0;      // async reset
    else if (en)     q <= q + 1'b1;  // register update
endmodule

wire y = a & b | c;                  // combinational net
assign sum = a + b;                  // continuous assignment
```
- `reg` = holds a value in a procedural block (may infer FF or latch); `wire` = a net driven by `assign`/output. `logic` in SystemVerilog replaces both.
- Widths matter: `4'b1010`, `8'hFF`, `1'b0`. Mismatched widths silently zero/truncate.

## VHDL basics
```vhdl
process(clk, rst)
begin
  if rst = '1' then q <= (others => '0');
  elsif rising_edge(clk) then
    if en = '1' then q <= q + 1; end if;
  end if;
end process;
y <= a and b;   -- concurrent (combinational)
```
- Strongly typed (`std_logic`, `std_logic_vector`, `unsigned`/`signed` from numeric_std). `<=` is signal assignment; signals update at end of the process delta cycle (like non-blocking).

## Synchronous design & clocking
- **Single clock domain, edge-triggered**: register everything off one clock edge -> predictable, static-timing-analyzable design. This is the discipline that makes FPGAs work reliably.
- **Reset**: pick sync or async-assert/sync-deassert; be consistent. Async reset needs deassertion synchronized to avoid recovery/removal violations.
- Don't gate clocks in the fabric (glitches); use **clock enables** instead. Generate related clocks via PLL/MMCM, not by dividing with logic/ripple.
- **No combinational feedback loops** (output feeds its own input with no register) — unstable / oscillates / untimeable.

## FSMs
- Encode state in a register; two- or three-process style: (1) sequential state register, (2) combinational next-state logic, (3) combinational/registered outputs.
- Use enumerated/localparam states. Register outputs (Moore, glitch-free) when driving other clocked logic. Define a default/`others` case -> avoids inferred latch and handles illegal states (add recovery to a safe state).

## Metastability & CDC
- A FF sampling an input that violates **setup/hold** goes **metastable** (output hangs between 0/1) and resolves unpredictably — corrupts downstream logic.
- **Clock Domain Crossing**: any signal from clock A used in clock B must be synchronized. Single-bit: **2-FF (double-flop) synchronizer** in the destination domain (add a 3rd for high MTBF).
- **Multi-bit buses across domains cannot use per-bit sync** (bits skew, capturing invalid combinations). Use a **handshake** (req/ack), **gray-coded** counter (async FIFO pointers), or an **async FIFO** (dual-clock BRAM).
- MTBF improves exponentially with added synchronizer stages and clock period.

## Timing & constraints
- **Setup time**: data must be stable before the clock edge; **hold time**: stable after. Violations -> metastability/wrong capture.
- Static Timing Analysis (STA) checks all paths against constraints. **Fmax** limited by the longest combinational path between registers (`Tclk >= Tco + Tlogic + Trouting + Tsetup - Tskew`).
- **Constraints (SDC/XDC)**: define clocks (`create_clock`), input/output delays, false paths, multicycle paths, and pin/IO assignments. Unconstrained clocks/paths => the tool doesn't optimize/verify timing => silent field failures.
- Pipeline (add register stages) to break long combinational paths and raise Fmax at the cost of latency.

## Synthesis vs simulation
- **Simulation** runs your testbench in an event simulator (with delays, `initial`, `$display`, `#10`) — verifies behavior. **Synthesis** turns RTL into gates; it ignores timing delays, `initial` (mostly), and non-synthesizable constructs.
- **Sim/synth mismatch** happens when code relies on simulation-only semantics (delays, incomplete sensitivity lists, blocking/non-blocking misuse). Aim for RTL that means the same thing to both.

## Testbenches
- Non-synthesizable driver: generate clock (`always #5 clk=~clk;`), apply stimulus, check outputs (self-checking with assertions/expected vs actual), report pass/fail. Cover reset, edge cases, back-to-back transactions. Use `$dumpvars` for waveforms.

## Gotchas -> Fix
- **Blocking `=` in a clocked block** (or `<=` in combinational): sim/synth mismatch, wrong pipelining, races. Fix: `<=` in `posedge` blocks, `=`/`assign` in combinational.
- **Inferred latch**: a combinational `always`/`case` that doesn't assign the output in every branch. Fix: default assignment at top, `default:`/`else`, full sensitivity `@(*)`.
- **CDC without synchronizer**: metastability, intermittent glitches that pass in sim. Fix: 2-FF sync for single bits, async FIFO/handshake/gray code for buses; mark with CDC constraints.
- **Combinational loop**: unstable/oscillation, timing failure. Fix: insert a register in the loop.
- **Incomplete sensitivity list** (`always @(a)` missing `b`): sim uses stale value, synth infers full list -> mismatch. Fix: `always @(*)` / `always_comb`.
- **Gated/rippled clock or logic-divided clock**: glitches, skew, unroutable. Fix: clock enable + PLL/MMCM-generated clocks; single-source clocks.
- **Multiple drivers on one net / `X` propagation**: contention. Fix: one driver per signal; trace `X` back to uninitialized reg or conflict.
- **Race in simulation** from blocking assignments across blocks reading each other. Fix: strict non-blocking discipline for sequential logic.
- **Reset not synchronized (async deassert)**: recovery/removal timing violation, random startup state. Fix: async assert + synchronous deassert (reset synchronizer).
- **Unconstrained design**: meets timing in the tool report but fails in hardware. Fix: full SDC/XDC — clocks, IO delays, false/multicycle paths.
- **Width mismatch / signed-unsigned**: silent truncation or wrong arithmetic. Fix: explicit widths, `signed`/`unsigned` (numeric_std), sign-extend deliberately.
- **Using BRAM/DSP inefficiently** (huge register arrays in LUTs). Fix: infer/instantiate block RAM and DSP with the recommended coding template.
- **`initial` values relied on for hardware state**: not guaranteed on all FPGAs/ASICs. Fix: explicit reset logic.
