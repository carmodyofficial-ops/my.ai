# Assembly Language

Human-readable mnemonics for machine instructions. One line ≈ one CPU instruction. Architecture-specific (ISA). Educational / reverse-engineering / performance / embedded context. Two big families below: **x86-64** and **ARM (AArch64)**.

## Registers
- **x86-64** general-purpose (64-bit / 32 / 16 / 8): `rax/eax/ax/al`, `rbx`, `rcx`, `rdx`, `rsi`, `rdi`, `rbp`, `rsp`, `r8`–`r15`. Writing a 32-bit reg (`eax`) **zeroes the upper 32 bits**; 8/16-bit writes don't. `rip` = instruction pointer, `rsp` = stack pointer, `rflags` = flags.
- **ARM64**: `x0`–`x30` (64-bit), `w0`–`w30` (32-bit views), `sp`, `pc`, `xzr`/`wzr` (zero register), `x30`=LR (link register).
- Registers are fast, finite; memory is large, slow.

## Syntax dialects (x86)
- **AT&T** (GNU `as`, gcc): `mov src, dest`, `%rax`, `$5` immediate, `(%rbx)` deref, sizes as suffixes `movq`/`movl`/`movb`.
- **Intel** (NASM, MASM, most disassemblers): `mov dest, src`, no sigils, `[rbx]` deref, `mov qword [x], 5`. Order is **reversed** between them.

## Memory & addressing modes (x86 Intel)
- Immediate `mov rax, 5`; register `mov rax, rbx`; direct `[addr]`; register-indirect `[rax]`; base+disp `[rbp-8]`; **base + index*scale + disp** `[rax + rcx*4 + 8]` (scale ∈ 1,2,4,8) — one instruction for array indexing. `lea rax, [rbx+rcx*4]` computes the address without a memory access (also used for arithmetic).

## Core instructions
- Data: `mov`, `lea`, `push`/`pop`, `xchg`, `movzx`/`movsx` (zero/sign extend).
- Arithmetic/logic: `add sub imul idiv inc dec neg`, `and or xor not`, `shl shr sar`, `cmp` (subtract, set flags, discard), `test` (AND, set flags). `xor rax, rax` = fast zero.
- Control: `jmp`; conditional `je/jz jne/jnz jg jl jge jle ja jb` (a/b = unsigned, g/l = signed) — based on flags from a prior `cmp`/`test`. `call`/`ret`, `loop`.
- ARM64 equivalents: `mov add sub mul`, `ldr`/`str` (all memory access via load/store — RISC), `cmp`, `b`/`b.eq`/`bl` (branch-with-link=call), `ret`.

## Flags (x86 RFLAGS)
- `ZF` zero, `SF` sign, `CF` carry (unsigned overflow), `OF` signed overflow, `PF` parity. Set by arithmetic/`cmp`/`test`; read by conditional jumps and `setcc`/`cmovcc`.

## The stack & calling conventions
- Stack grows **downward** (toward lower addresses); `rsp` -> top. `push` decrements `rsp` then stores; `pop` loads then increments. `call` pushes return address; `ret` pops it into `rip`.
- **System V AMD64 ABI** (Linux/macOS): integer/pointer args in `rdi, rsi, rdx, rcx, r8, r9`, then stack; return in `rax` (`rdx:rax` for 128-bit). Callee-saved: `rbx, rbp, r12–r15` (must preserve); caller-saved (scratch): `rax, rcx, rdx, rsi, rdi, r8–r11`. **16-byte stack alignment** required at `call`. 128-byte **red zone** below `rsp` usable in leaf functions. Floats in `xmm0–7`; `al` = # of vector regs for varargs.
- **Windows x64**: args `rcx, rdx, r8, r9`; 32-byte shadow space; different callee-saved set.
- **ARM64 (AAPCS)**: args `x0–x7`, return `x0`; `x19–x28` callee-saved; `x30`=return addr.
- Typical prologue: `push rbp; mov rbp, rsp; sub rsp, N`; epilogue `leave; ret` (or `mov rsp, rbp; pop rbp`).

## Syscalls (Linux x86-64)
- `syscall` instruction. Number in `rax`; args in `rdi, rsi, rdx, r10, r8, r9` (note `r10`, **not** `rcx` — `syscall` clobbers `rcx`/`r11`). Return in `rax` (negative = `-errno`). e.g. `write` = 1, `exit` = 60. ARM64 uses `svc #0`, number in `x8`.

## Sections & the toolchain
- `.text` = code (executable, read-only); `.data` = initialized globals; `.bss` = zero-initialized/uninitialized (no file space); `.rodata` = constants. Directives: `.global`/`.globl` (export symbol), `.section`, labels `main:`.
- **Assembler** (`as`, `nasm`) turns `.s`/`.asm` -> object `.o`. **Linker** (`ld`, or `gcc` driver) combines objects + libs, resolves symbols/relocations -> executable. `objdump -d` / `gdb` / Ghidra / IDA to disassemble.

## SIMD & FPU (brief)
- x86 SSE/AVX use `xmm0–15`/`ymm`/`zmm` registers for packed float/int (`addps`, `mulps`, `movaps` — aligned, `movups` — unaligned). Scalar float in `xmm` (`addsd`/`movsd`). Floats passed/returned in `xmm0–7` under System V. ARM uses `v0–v31` NEON/SVE.

## Common patterns to recognize (reverse engineering)
- `xor reg,reg` = zero; `test rax,rax` + `je` = null/zero check; `lea` doing arithmetic (not addressing); `push rbp; mov rbp,rsp` = stack-frame setup; `rep movsb`/`stosb` = memcpy/memset; jump table (`jmp [rax*8+table]`) = compiled `switch`; PLT stub + `@plt` = external library call; canary check (`mov rax, fs:[0x28]` ... `__stack_chk_fail`).
- Optimized code inlines, reorders, and uses `cmov`/branchless tricks; `-O0` maps almost line-for-line to source.

## Relation to C
- C compiles to asm (`gcc -S`, `-O0`..`-O3`). Local vars -> stack `[rbp-N]` or registers; struct fields -> offsets; function call -> ABI arg-passing + `call`; pointers -> addresses. Reading compiler output is the fastest way to learn asm and to reverse-engineer.

## Gotchas -> Fix
- **Stack misalignment**: `call` requires `rsp` 16-byte aligned; an odd number of pushes before calling libc (e.g. `printf`) crashes on SSE/`movaps` -> keep pushes even or `sub rsp, 8` to realign; account for the 8-byte return address.
- **Clobbering callee-saved regs** without save/restore corrupts the caller -> `push`/`pop` `rbx`, `r12–r15`, `rbp` if you use them.
- **Assuming caller-saved regs survive a `call`**: `rax, rcx, rdx, rsi, rdi, r8–r11` may be trashed by the callee -> save across calls or use callee-saved regs.
- **`syscall` uses `r10` not `rcx`** for the 4th arg, and destroys `rcx`/`r11` -> load `r10`.
- **AT&T vs Intel operand order reversed** -> know your assembler; disassemblers default to Intel, GNU `as` to AT&T.
- **Endianness**: x86/ARM little-endian; multi-byte value `0x12345678` stored low-byte-first -> matters when reading raw memory dumps / network (big-endian) data; `bswap`/`rev`.
- **Operand size / partial registers**: forgetting size (`mov [x], 5` ambiguous) -> specify (`mov qword [x], 5`); 32-bit writes zero upper bits, 8/16-bit don't (false dependencies).
- **Signed vs unsigned jumps**: use `jg/jl` after signed `cmp`, `ja/jb` after unsigned — mixing gives wrong branches.
- **`div`/`idiv`**: divides `rdx:rax`; forgetting to zero/sign-extend `rdx` (`cqo`/`xor rdx,rdx`) -> garbage or #DE fault.
- **Forgetting to exit**: falling off `main` past code into data -> illegal instruction; call `exit` syscall or `ret` properly.
- **PIE/relocations**: modern binaries are position-independent; absolute addresses fail -> use `rip`-relative (`lea rax, [rip+sym]`) or GOT/PLT.
