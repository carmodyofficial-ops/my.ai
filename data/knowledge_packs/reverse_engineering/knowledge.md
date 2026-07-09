# Reverse Engineering (Defensive / Educational)

Scope: authorized, lawful use only — malware analysis and incident response, debugging your own software, interoperability, security research on systems you own/are permitted to test, and CTF. Understand behavior and structure; no weaponization.

## Static vs Dynamic Analysis
- Static: analyze without executing — disassembly, decompilation, string/import triage, control-flow/data-flow reasoning. Safe (no detonation), complete coverage of code paths, but defeated by packing/obfuscation and can't resolve runtime-computed values.
- Dynamic: run under instrumentation — debugger, tracer, sandbox — to observe real behavior (syscalls, network, files, unpacked code). Reveals what static hides but only exercises taken paths and risks detonating live malware -> always isolate.
- Practice: iterate. Static triage to form hypotheses → dynamic to confirm and to reach unpacked code → static on the dumped/unpacked image.

## Binary Formats
- ELF (Linux/Unix): header (magic `\x7fELF`, class 32/64, endianness, entry point), program headers (segments — loader's view: LOAD/DYNAMIC/INTERP), section headers (linker/analysis view). Key sections: `.text` (code), `.data` (init RW), `.rodata` (const), `.bss` (zero-init, no file bytes), `.plt`/`.got` (dynamic call/relocation stubs), `.symtab`/`.dynsym` (symbols), `.rela.*` (relocations).
- PE (Windows): DOS stub → PE header → optional header (entry `AddressOfEntryPoint`, `ImageBase`) → section table (`.text`/`.data`/`.rdata`/`.rsrc`). Import Address Table (IAT) resolves DLL functions; export table; resources.
- Mach-O (macOS): load commands, segments/sections, `LC_MAIN` entry.
- Symbols/relocations aid analysis; stripped binaries lack `.symtab` (function names gone — recover via signatures/FLIRT-style matching, strings, imports).

## Calling Conventions & Stack Frames
- System V AMD64 (Linux/mac): integer args in `rdi, rsi, rdx, rcx, r8, r9`, return in `rax` (`rdx:rax` for 128-bit); floats in `xmm0-7`. Callee-saved: `rbx, rbp, r12-r15`; caller-saved: the rest. 16-byte stack alignment at call.
- Windows x64: args `rcx, rdx, r8, r9` + 32-byte "shadow space" reserved by caller; return `rax`.
- x86 (32-bit): cdecl (args on stack right-to-left, caller cleans), stdcall (callee cleans — WinAPI), fastcall.
- Stack frame: `call` pushes return address; prologue `push rbp; mov rbp, rsp; sub rsp, N` sets frame; locals at `[rbp-x]`, args (32-bit) at `[rbp+x]`; epilogue `leave; ret`. Frame-pointer omission (`-fomit-frame-pointer`) complicates unwinding — rely on debug/unwind info (DWARF `.eh_frame`).

## Reading Assembly
- Common x86-64: `mov` (copy), `lea` (compute address / cheap arithmetic), `add/sub/imul`, `cmp`+`test` set flags, `jz/jnz/jg/jle` conditional jumps, `call/ret`, `push/pop`, `xor reg,reg` (zero idiom). AT&T (`src, dst`) vs Intel (`dst, src`) syntax — know which your tool shows.
- Recognize patterns: loops (back-edge + counter), switch (jump table via `.rodata`), struct access (`base+offset`), array (`base + index*scale`), string ops (`rep movs/stos`), stack canary (`fs:0x28` load + check before ret), PIC via GOT/PLT.
- Decompilers reconstruct C-like pseudocode from disassembly (control-flow structuring, type/variable recovery) — great for comprehension but lossy/heuristic; verify against the disassembly for correctness-critical claims.

## Tooling (categories, generic)
- Disassemblers/decompilers with interactive analysis, cross-references, type reconstruction (interactive RE platforms).
- Debuggers: source/assembly-level (`gdb`, `lldb`, WinDbg, x64dbg).
- Dynamic instrumentation/tracing: syscall tracers (`strace`/`dtruss`), library tracers (`ltrace`), DBI frameworks, function-hooking.
- Triage utilities: `file`, `strings`, `nm`, `objdump`, `readelf`/`dumpbin`, `xxd`, hash/entropy tools, YARA (signature matching).
- Sandboxes: instrumented VMs capturing filesystem/registry/network/process behavior.

## Debuggers
- Software breakpoint: overwrite target byte with `int3` (`0xCC`); debugger restores original on hit, single-steps over, reinserts. Detectable (code checksum/`0xCC` scan).
- Hardware breakpoint: CPU debug registers (`DR0-DR3` + `DR7`) — up to 4, no code modification; also enable data watchpoints.
- Watchpoint: break on read/write/access to an address — find who mutates a variable.
- Stepping: step-into (`si`, enters calls), step-over (`ni`), step-out (finish frame). Examine memory/registers (`x`, `info registers`), set conditional breakpoints to skip noise.

## Triage Workflow
- Identify: `file`/magic, arch/bitness, packer/compiler signatures, section entropy (high, ~7.9+ bits/byte, or tiny `.text` + huge `.data` ⇒ likely packed/encrypted).
- `strings` (and wide/UTF-16 strings): URLs, IPs, file paths, registry keys, commands, error messages, crypto constants — cheap high-signal leads. Beware obfuscated/stacked strings assembled at runtime.
- Imports/exports: capability inference (`socket`/`connect` net, `CreateProcess`/`WinExec` exec, `RegSetValue` persistence, `CryptEncrypt` crypto, `VirtualAlloc`+`WriteProcessMemory` injection). Few/no imports + `LoadLibrary`/`GetProcAddress` ⇒ dynamic resolution to hide intent.
- Hashes (MD5/SHA-256, imphash, fuzzy ssdeep) → threat-intel lookup and clustering. Map behavior to ATT&CK.

## Dynamic Analysis Techniques
- Syscall/API tracing: enumerate the OS-level actions (open/read/write/connect/exec, registry, process/thread creation) → behavioral profile independent of obfuscated internals. Library-call tracing catches libc/WinAPI usage.
- Sandboxing: instrumented VM records filesystem/registry/network/process activity over a timed run; fakenet/inetsim serves fake C2 so the sample proceeds without real infrastructure. Snapshot before run, revert after.
- Memory forensics: dump process memory to recover unpacked code, decrypted config, injected payloads, cleartext strings/keys the packed file never showed statically.
- Emulation / DBI: run in an emulator or dynamic binary instrumentation framework to trace every instruction, hook APIs, and force paths; symbolic/concolic execution derives inputs that reach a target block.
- Network: capture traffic (pcap), decode C2 protocol, extract IOCs (domains/IPs/URIs/user-agents); TLS interception via a controlled proxy on a test host to see plaintext.

## Interoperability & Legit RE
- Recover undocumented file/wire formats: diff outputs across inputs, hex-inspect for magic/length/offset fields, correlate with observed behavior. Clean-room reimplementation (spec team separate from impl team) to avoid copyright taint.
- Debugging without source: symbolize with available PDB/DWARF; reconstruct types from usage; validate hypotheses by patching + observing.

## Obfuscation & Anti-Analysis (how analysts handle)
- Packing/crypting: compressed/encrypted payload + runtime unpacking stub. Handle: run to original entry point (OEP) after unpacking, dump process memory, fix imports/rebuild IAT; or emulate the stub.
- String/API obfuscation (stacked strings, XOR/RC4, API hashing): recover via emulation, scripting the decode, or breakpoint on the decryptor and read decoded data.
- Anti-debugging: `IsDebuggerPresent`/PEB `BeingDebugged`, `NtQueryInformationProcess`, timing checks (`rdtsc` deltas), `int3`/`0xCC` scans, exception-based detection, hardware-breakpoint (DR) checks. Handle: hide-debugger plugins, patch checks, hardware breakpoints, or full-system emulation.
- Anti-VM/sandbox: probe MAC OUIs, device names, CPUID hypervisor bit, low core/RAM, user-idle/no-artifacts, sleep/stalling to outlast sandbox timeout. Handle: harden/disguise the sandbox, patch checks, extend timeouts, bare-metal detonation.
- Control-flow obfuscation: flattening, opaque predicates, junk/dead code, self-modifying code — analyze dynamically, use symbolic/concolic execution to prune infeasible paths.

## Disassembly Internals
- Linear-sweep disassembly decodes sequentially (fast, but data-in-code desyncs it); recursive-descent/traversal follows control flow (accurate, misses indirect/dynamically-computed targets). Interactive tools combine both plus user annotations.
- x86 variable-length encoding (1-15 bytes) means starting one byte off yields a completely different valid-looking instruction stream — anchor on known entry points and function prologues.
- Signature/library recognition (FLIRT-style) labels statically-linked library functions so you focus on original code. Cross-references (xrefs) map who-calls-what and who-reads/writes-data — central to navigation.

## Practical Recon Signals
- Entropy per section flags packing/encryption; abnormal section names or a tiny `.text` with a huge writable segment suggest a stub + payload.
- Timestamp, compiler/linker signature, rich header (PE) hint at toolchain and build lineage. Overlay data appended past the last section often holds payloads/configs.
- Cryptographic constants (AES S-box, SHA/MD5 init values, base64 alphabet) betray algorithms; hardcoded keys/IVs sometimes recoverable statically.

## Pitfalls -> Fix
- Detonating live malware on a networked host -> isolated VM/air-gapped or fake-net, snapshots, no shared folders/creds; assume the sample is hostile.
- Trusting decompiler output as ground truth -> cross-check pseudocode against disassembly for anything correctness-critical; decompilation is heuristic.
- Analyzing a packed binary statically and seeing only the stub -> unpack dynamically to OEP and dump before static analysis.
- Static-only on malware with dynamic API resolution -> imports look empty; trace `GetProcAddress`/`LoadLibrary` at runtime to recover the real call graph.
- Breakpoint detected via code checksum/`0xCC` scan -> use hardware breakpoints instead of software `int3`.
- Wrong disassembly from data-in-code or misaligned start -> mark data regions; verify instruction boundaries; variable-length x86 desyncs easily.
- Assuming the wrong calling convention when reading args -> confirm platform ABI (SysV vs Windows x64, cdecl vs stdcall) before interpreting register/stack operands.
- Sandbox reports "benign" because sample stalled or VM-detected -> extend runtime, defeat anti-VM checks, try bare metal; absence of behavior ≠ safe.
- Losing analysis state on a self-modifying/relocating target -> work on a dumped snapshot at a stable point; re-run to reproduce.
