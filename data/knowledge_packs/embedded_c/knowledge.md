# Embedded C

## Bare-metal model
- No OS, no `main()` runtime guarantees beyond what startup code sets up. Reset vector -> startup (`Reset_Handler`) -> copy `.data` from flash to RAM, zero `.bss`, set stack pointer, call `main()`. `main()` never returns (`while(1)` super-loop or RTOS).
- Program in flash (XIP), variables in RAM. No `printf` unless you retarget `_write`/`putchar` to a UART. No heap unless you provide `_sbrk`.
- CPU talks to peripherals via **memory-mapped registers** at fixed addresses (Cortex-M peripherals at `0x4000_0000+`). Reading/writing an address = reading/writing hardware.
- Single-purpose, deterministic, resource-constrained (KB of RAM, MHz clocks). Every byte and cycle counts.

## Memory-mapped registers + volatile
- Access via pointer to volatile: `#define GPIOA_ODR (*(volatile uint32_t*)0x48000414)`. Vendor headers give structs: `GPIOA->ODR |= (1<<5);`.
- **`volatile` is mandatory** for any memory changed outside normal flow: hardware registers, variables shared with ISRs, memory-mapped I/O. Without it the optimizer caches the value in a register and your poll loop `while(!(REG & FLAG));` spins forever or the write is dropped.
- `volatile` does NOT give atomicity or memory ordering — only prevents the compiler from optimizing away/reordering the access. For ordering across peripherals use `__DMB()`/`__DSB()` barriers.
- Read-modify-write on a register (`REG |= x`) is 3 instructions — not atomic vs an ISR touching the same register. Use bit-band, atomic set/clear registers (`BSRR` on STM32), or disable interrupts around it.

## Bit manipulation
```c
reg |=  (1u << n);        // set bit n
reg &= ~(1u << n);        // clear bit n
reg ^=  (1u << n);        // toggle bit n
if (reg & (1u << n)) ...  // test bit n
reg = (reg & ~mask) | (val << shift);  // set a field
```
- Use `1u`/`1UL` (unsigned) — `1<<31` is UB on signed int. Multi-bit field: mask first, then OR. Named masks/positions beat magic numbers.

## GPIO + peripherals
- **GPIO**: configure mode (input/output/alt-func/analog), pull-up/down, speed. Then read `IDR` / write `ODR`/`BSRR`. Configure clock gating first (`RCC->AHBENR |= ...`) — a peripheral with no clock reads as 0 and ignores writes.
- **UART**: set baud (BRR = fck/baud), enable TX/RX, poll `TXE`/`RXNE` or use interrupt/DMA. Frame = start + 8 data + parity? + stop. Async, no clock line.
- **SPI**: master drives SCLK, full-duplex (MOSI/MISO), CS per slave. Modes 0-3 = CPOL/CPHA. Fast (MHz), short range. Write to DR sends + receives simultaneously.
- **I2C**: 2-wire (SDA/SCL) open-drain, needs external pull-ups (~4.7k). 7-bit addr + R/W bit, ACK/NACK, START/STOP. Slower (100k/400k/1M). Clock stretching by slaves.
- **ADC**: successive-approximation, N-bit -> `code = Vin/Vref * (2^N - 1)`. Sample time must exceed source impedance settling. Oversample/average to gain bits.
- **PWM (timer)**: period = ARR, duty = CCR. `freq = timer_clk / ((PSC+1)*(ARR+1))`. Duty% = CCR/(ARR+1).
- **Timers**: prescaler + auto-reload counter; use for periodic interrupts, input capture (measure pulse), output compare.

## Interrupts + ISRs
- NVIC (Cortex-M): enable IRQ, set priority (lower number = higher prio), write handler with the exact linker-expected name (`TIM2_IRQHandler`).
- **Keep ISRs short**: clear the interrupt flag, set a `volatile` flag / push to a ring buffer, return. Defer heavy work to the main loop or an RTOS task.
- Shared state between ISR and main **must be `volatile`**; multi-byte shared data needs a critical section (`__disable_irq()`/`__enable_irq()` or `BASEPRI`) or a lock-free single-producer/single-consumer ring buffer.
- **Never block in an ISR** (no `delay`, no busy-wait on another interrupt, no mutex that can sleep). Never call non-reentrant/blocking library funcs.
- Always clear the pending flag or the ISR re-fires immediately (interrupt storm). Watch priority: a higher-prio IRQ preempts a lower one — nested critical sections needed.

## Memory discipline
- **Avoid dynamic allocation** (`malloc`/`free`): fragmentation, nondeterministic timing, silent OOM, no MMU. Prefer static/global buffers, fixed pools, stack. If you must, allocate once at init and never free.
- Stack lives in RAM and grows down; overflow silently corrupts `.bss`/heap. Size it from worst-case call depth + ISR nesting; fill with a pattern and check high-water mark.
- `const` data stays in flash (saves RAM). Place large lookup tables in flash.

## Fixed-point
- No FPU on many MCUs -> float is slow/emulated. Use integer fixed-point: Q16.16 stores `x*65536`. Multiply: `(int64_t)a*b >> 16`. Add/sub directly. Round before shift: `(a + (1<<15)) >> 16`.

## Watchdog, linker, debug
- **Watchdog (IWDG/WDT)**: hardware timer that resets the MCU unless kicked periodically. Kick in the main loop only after verifying the system is healthy — kicking from a timer ISR defeats the purpose.
- **Linker script (`.ld`)**: defines memory regions (FLASH origin/len, RAM) and sections (`.text`,`.rodata` -> flash; `.data`,`.bss` -> RAM). `.data` has LMA in flash, VMA in RAM; startup copies it. Place ISR vector table at flash origin.
- **Debug**: SWD (2-wire: SWDIO/SWCLK) or JTAG (5-wire) via ST-Link/J-Link. Breakpoints, single-step, watchpoints, RAM/register inspect. SWO/ITM for `printf`-style trace without a UART. Semihosting is convenient but halts the core — remove for production.

## Gotchas -> Fix
- **Missing `volatile`** on register/ISR-shared var: poll loop hangs or writes vanish. Fix: declare `volatile`; re-read the datasheet's access rules.
- **`volatile` mistaken for atomic**: torn 16/32-bit read across an ISR. Fix: critical section or SPSC ring buffer; use atomic set/clear registers for GPIO.
- **RMW on shared register** (`REG |= x`) races the ISR. Fix: `BSRR`-style atomic set/clear regs, or disable IRQ around it.
- **Peripheral clock not enabled**: register reads 0, writes ignored, "dead" peripheral. Fix: set `RCC` enable bit first, then configure.
- **Blocking / long work in ISR**: missed deadlines, dropped interrupts, watchdog reset. Fix: flag-and-defer to main loop/task.
- **Flag not cleared in ISR**: interrupt re-fires forever. Fix: clear the source flag (often read-then-write, or write-1-to-clear per datasheet).
- **Stack overflow**: corrupts `.bss`, random crashes. Fix: size stack for worst case, fill-pattern high-water check, watch deep recursion/large local arrays.
- **Integer promotion / signedness**: `uint8_t a=200,b=100; a+b` promotes to `int` (300) then truncates on store; `1<<31` on signed int is UB. Fix: use `unsigned`/explicit widths, `1u<<n`, cast intermediates.
- **`==` vs `=` in register test** compiles fine, wrong logic. Enable `-Wall -Wextra`.
- **Buffer used before DMA finishes**: garbage data. Fix: wait for transfer-complete flag; mark DMA buffers `volatile`; mind cache coherency on Cortex-M7 (clean/invalidate).
- **Enum/struct padding + register overlay**: use `packed` structs only for byte layouts; never assume compiler packs registers — use the vendor CMSIS header.
- **`delay()` calibrated loop varies with optimizer/clock**: use a hardware timer for real timing.
- **Signed shift of negative / undefined width shift** (`x << 32` on 32-bit): UB. Mask shift amount.
