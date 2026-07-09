# Electronics Fundamentals

## Ohm's law & power
- `V = I·R` (volts = amps × ohms). Rearrange: `I = V/R`, `R = V/I`.
- Power: `P = V·I = I²·R = V²/R` (watts). Resistor heating = `I²R` — size wattage with margin (a 1/4W resistor at 0.3W burns).
- Units: mA = 10⁻³ A, kΩ = 10³ Ω, µF = 10⁻⁶ F, nF = 10⁻⁹ F, pF = 10⁻¹².

## Series & parallel
- **Series** (same current): `R_total = R1 + R2 + ...`; voltages add; caps combine like parallel resistors (`1/C = 1/C1+...`).
- **Parallel** (same voltage): `1/R_total = 1/R1 + 1/R2 + ...`; two resistors: `R = R1·R2/(R1+R2)`; currents add; caps add (`C = C1+C2`).
- Parallel resistance is always **less** than the smallest resistor.

## Kirchhoff's laws
- **KCL (current)**: sum of currents into a node = sum out (charge conserved). `ΣI_in = ΣI_out`.
- **KVL (voltage)**: sum of voltage drops around any closed loop = 0 (energy conserved).
- These + Ohm's law solve any resistive network.

## Voltage divider
- Two series resistors from V to GND, tap between: `V_out = V_in · R2/(R1+R2)`.
- Valid only when the load draws negligible current vs the divider (load ≫ R2, or the tap sags). Not a power supply — for reference/sensing only.
- Potentiometer = adjustable divider.

## Components
- **Resistor**: limits current, sets bias/dividers. Color bands or 3-4 digit code. Tolerance ±1/5%. No polarity.
- **Capacitor**: stores charge, `Q = C·V`; **blocks DC, passes AC**; impedance `Z_C = 1/(2πfC)` (high at low freq). Uses: decoupling, filtering, timing, coupling. Electrolytic/tantalum are **polarized** (reverse = pop); ceramic is not. Voltage rating must exceed rail with margin.
- **Inductor**: stores energy in magnetic field; **passes DC, opposes AC/change** in current; `Z_L = 2πfL`; `V = L·di/dt`. Uses: filters, switching regulators, chokes. Sudden current interruption -> large voltage spike (flyback).
- **Diode**: one-way valve; conducts when forward-biased above ~0.7V (Si) / ~0.3V (Schottky) / LED ~1.8-3.3V. Uses: rectification, reverse-polarity protection, flyback clamp. Zener conducts in reverse at a set voltage (regulation/reference).
- **BJT** (current-controlled): small base current controls larger collector current, `Ic = β·Ib`. NPN on when base ~0.7V above emitter. As a switch: saturate it (enough base current).
- **MOSFET** (voltage-controlled): gate voltage controls drain-source channel; near-zero gate current. N-channel on when `Vgs > Vth`. Low `Rds(on)` -> efficient switch. Preferred power switch. Needs gate pull-down so it defaults off.

## RC time constant
- `τ = R·C` (seconds). Charging: `V(t) = V_final·(1 − e^(−t/τ))`; ~63% at 1τ, ~99% at 5τ. Discharge mirrors.
- Sets timing delays, debounce, and filter corner: **cutoff `f_c = 1/(2πRC)`**. Low-pass (R then C to GND) passes low freq; high-pass swaps them.

## Pull-up / pull-down
- Resistor (typ 1k-100k, often 10k) tying a line to VCC (pull-up) or GND (pull-down) so a floating/high-Z input has a **defined default** level.
- Needed for: MCU inputs, open-drain buses (**I2C requires external pull-ups**, ~4.7k), buttons. Value: too high -> noise-susceptible/slow edges; too low -> wasted current.

## Digital logic
- Gates: NOT, AND, OR, NAND, NOR, XOR, XNOR. NAND/NOR are universal. Truth tables define behavior.
- Logic levels: TTL/CMOS thresholds; 3.3V vs 5V domains need level shifting. Logic HIGH ≈ VCC, LOW ≈ GND, with a forbidden mid-band.
- Combinational (output = f(inputs)) vs sequential (flip-flops, memory, clocked).

## ADC / DAC
- **ADC**: analog -> digital. N-bit -> `2^N` levels; `code = round(V_in/V_ref · (2^N − 1))`; resolution/LSB `= V_ref/2^N`. Sampling must satisfy **Nyquist** (f_s > 2× signal bandwidth) or aliasing corrupts. Anti-alias filter before sampling.
- **DAC**: digital -> analog; `V_out = code/2^N · V_ref`. Follow with a reconstruction (low-pass) filter.

## Decoupling / bypass caps
- Place a **0.1µF ceramic right at each IC's power pin** (VCC-GND) to supply instantaneous switching current and suppress noise; add bulk (1-100µF) per board/rail. Short traces = low inductance. Missing/ far caps -> glitches, resets, EMI, flaky behavior.

## Reading schematics / build flow
- Symbols: lines = wires, junction dots = connected, no dot = crossing. GND and VCC nets by symbol/label. Reference designators: R#, C#, U# (IC), Q# (transistor), D# (diode), J# (connector).
- Flow: **breadboard** (prototype, no soldering, has parasitic C/L — bad above a few MHz) -> perfboard/soldered -> **PCB** (layout, ground plane, controlled routing).
- **Multimeter**: DC/AC volts, current (in series, move probe), resistance/continuity (power OFF), diode test. **Oscilloscope**: waveform vs time — edges, ripple, timing, noise; set probe 10×, mind bandwidth and ground lead.

## Gotchas -> Fix
- **Missing decoupling caps**: random resets, noise, EMI. Fix: 0.1µF at every IC power pin + bulk cap per rail, short traces.
- **Floating input**: reads random / oscillates / draws current. Fix: pull-up or pull-down (10k typ), or drive the pin.
- **Insufficient current / weak supply**: voltage sags, MCU browns out, motor stalls. Fix: size supply for peak (not average) current; bulk caps for transients; thicker traces/wire.
- **Reverse polarity**: fries polarized caps/ICs, pops electrolytics. Fix: series diode or P-MOSFET protection, keyed connectors, double-check before power.
- **Ground loops / shared high-current return**: noise, offset, hum. Fix: single-point/star ground, separate analog & digital grounds joined at one point, ground plane.
- **No flyback diode on relay/motor/inductor**: switching transistor destroyed by inductive spike. Fix: reverse diode across the coil (or snubber).
- **Voltage divider used as a supply**: output collapses under load. Fix: use a regulator/buffer; dividers only for reference/sensing with high-impedance loads.
- **MOSFET gate left floating**: turns on/off randomly. Fix: gate pull-down (10-100k) to a known off state; drive gate fully (logic-level FET for 3.3/5V).
- **I2C without pull-ups**: bus stuck, no ACK. Fix: 4.7k pull-ups on SDA and SCL (once per bus).
- **Resistor/cap under-rated**: overheats or fails. Fix: pick wattage (≥2× dissipation) and cap voltage (≥1.5× rail) with margin.
- **Mixing 5V and 3.3V logic**: over-voltage on a 3.3V input. Fix: level shifter / divider; check pin abs-max.
- **Breadboard at high speed/current**: flaky due to contact resistance & parasitics. Fix: solder / PCB for RF, fast edges, or >1A.
- **Measuring current wrong**: meter in parallel blows its fuse. Fix: ammeter goes in series; voltmeter in parallel.
- **Scope ground lead making a big loop**: injects noise. Fix: short ground spring, 10× probe, proper bandwidth.
