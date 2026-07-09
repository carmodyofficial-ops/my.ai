# Zig

Low-level systems language: manual memory, no hidden control flow, no hidden allocation, compile-time execution (`comptime`), first-class C interop. Toolchain: `zig build`, `zig run`, `zig test`, `zig cc` (drop-in C compiler). Pre-1.0 — language/std churns between versions.

## Philosophy
- **No hidden control flow**: no exceptions, no operator overloading, no destructors/RAII, no implicit allocations. If code runs, you can see it.
- **No hidden allocation**: anything that allocates takes an `Allocator` parameter explicitly.
- Errors are values (error unions), not exceptions.

## Memory & allocators
- No default global allocator. Pass `std.mem.Allocator` explicitly. Common: `std.heap.GeneralPurposeAllocator` (debug: detects leaks/double-free), `std.heap.page_allocator`, `ArenaAllocator` (free all at once), `FixedBufferAllocator` (stack buffer, no heap), `std.testing.allocator` (leak-checks tests).
```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();          // reports leaks
const a = gpa.allocator();
const buf = try a.alloc(u8, 100);
defer a.free(buf);
```
- **`defer`**: runs stmt at scope exit (LIFO). **`errdefer`**: runs only if function returns an error afterward — use to unwind partial allocation on the error path.

## Error unions & try
- Error set: `error{OutOfMemory, NotFound}`. Function returns `!T` (inferred error set) or `E!T`.
- `try expr` = unwrap or `return err` (propagate). `catch` handles: `foo() catch |err| { ... }`, `foo() catch default`, `foo() catch unreachable`.
- `errdefer` pairs with `try` for cleanup on failure.
- No ignoring errors: unused error union is a compile error.

## Optionals
- `?T` = value or `null` (separate from errors). Unwrap: `if (opt) |v| { ... } else { ... }`, `orelse default`, `opt.?` (asserts non-null, panics if null).
- Optional pointers `?*T` are zero-cost (null = 0), no separate tag.

## comptime
- Run code at compile time: `comptime` keyword, or automatically for type-level context. Types are first-class **values** at comptime: `fn List(comptime T: type) type { return struct { items: []T }; }` — this is how generics work (no separate generic syntax).
- `inline for`/`inline while` unroll at compile time. `comptime var` for compile-time mutable state.
- `@TypeOf`, `@typeInfo` for reflection; build code based on type structure.

## Slices vs arrays vs pointers
- Array `[N]T`: fixed length known at compile time, value type. `[5]u8`.
- Slice `[]T`: pointer + runtime length (`.ptr`, `.len`). Get one via `arr[a..b]` or `arr[0..]`.
- `[*]T` = many-item pointer (no length); `*T` = single-item; `[*c]T` = C pointer.
- Sentinel-terminated: `[:0]u8` (null-terminated slice), `[N:0]u8`. String literals are `*const [N:0]u8`.

## C interop
- `@cImport({ @cInclude("stdio.h"); })` pulls C decls directly. Link with `-lc`.
- Types map 1:1 (`c_int`, `[*c]u8`). No FFI boilerplate/bindings generator needed.
- `export fn` exposes Zig to C; `extern fn` declares C function. `zig cc` compiles C too.

## Build system
- `build.zig` is a Zig program building a graph of steps. `b.addExecutable(.{...})`, `b.addModule`, `exe.linkLibC()`. `build.zig.zon` = dependency manifest (package hashes).
- Cross-compile trivially: `zig build -Dtarget=aarch64-linux-musl`. Optimize modes: `Debug`, `ReleaseSafe`, `ReleaseFast`, `ReleaseSmall` (via `-Doptimize`).

## Structs / misc
- `struct`, `enum`, `union`, `tagged union` (`union(enum)` — switch with capture `switch (u) { .a => |v| ... }`), `packed struct` (bit layout), `extern struct` (C ABI layout). Methods: functions in struct namespace, called `obj.method()`.
- `pub` for exported. `usingnamespace` merges. `test "name" { ... }` inline tests run by `zig test`; `std.testing.expect`, `expectEqual`, `expectError`.
- Integer types explicit: `u8..u65535`, `i32`, `usize`/`isize` (pointer-width). Overflow: `+` panics in safe modes; use `+%` (wrapping), `+|` (saturating), `@addWithOverflow` (returns tuple). Casts: `@intCast`, `@floatFromInt`, `@ptrCast`, `@as(T, x)` (coerce), `@bitCast`.
- `anytype` param = comptime-duck-typed generic argument. `@import("std")` pulls the standard library; `@import("builtin")` build info.

## Control flow & idioms
- `if`/`else`, `while (cond) : (i += 1) {}` (continue expr), `for (slice) |item| {}`, `for (a, b) |x, y| {}` (parallel), `for (slice, 0..) |item, i| {}` (index). `switch` is exhaustive (must cover all cases or `else`), can range `1...5` and multi `.a, .b =>`.
- `break :label value` / `blk: { break :blk x; }` — labeled blocks yield values. No `goto`. Ternary via `if (c) a else b`.
- Struct/array/slice literals: `.{ .x = 1 }` (anonymous, inferred type), `[_]u8{1,2,3}` (inferred len). `.{}` empty.

## Common std pieces
- `std.ArrayList(T)` (growable, needs allocator: `.init(a)` / newer `.empty` + `.append(a, x)`), `std.AutoHashMap(K,V)`/`StringHashMap`, `std.mem` (`eql`, `copyForwards`, `split`, `tokenize`, `indexOf`), `std.fmt` (`std.debug.print("{d} {s}\n", .{n, s})`, `bufPrint`, `allocPrint`), `std.fs` (files), `std.json`, `std.Thread`.
- `std.debug.print` writes to stderr (no allocator); format specifiers `{d} {s} {any} {x} {?} {!}`.

## Testing & docs
- `test` blocks colocated; run `zig test file.zig` or `zig build test`. `std.testing.allocator` fails the test on leaks. Doc comments `///`; `zig build-obj -femit-docs`.

## Gotchas -> Fix
- **Use-after-free / dangling allocator**: returning a slice backed by a freed arena or a stack `FixedBufferAllocator` -> ensure allocator outlives the data; dupe into caller's allocator (`allocator.dupe`).
- **Forgetting `defer free`** -> leak; `GeneralPurposeAllocator.deinit()` / `testing.allocator` will report it. Pair every `alloc`/`create` with `defer free`/`destroy`.
- **`errdefer` vs `defer` confusion**: `defer` always runs; `errdefer` only on error return. Use `errdefer` to free resources allocated in a function that may still fail later.
- **`ReleaseFast`/`ReleaseSmall` remove safety checks**: undefined behavior (integer overflow, OOB, null `.?`, `unreachable`) that panicked in `Debug`/`ReleaseSafe` becomes real UB -> test in `ReleaseSafe`; use `ReleaseSafe` in prod if you want checks kept.
- **`undefined` is literal garbage**: `var x: u8 = undefined;` reading before writing is UB (GPA may poison to `0xAA`). Always initialize before read.
- **comptime confusion**: values must be comptime-known where required (array sizes, type params); passing a runtime value gives "unable to evaluate comptime" -> mark param `comptime` or restructure.
- **Slice `.len` is element count, not bytes**; `@sizeOf` for bytes.
- **Integer overflow panics** in safe modes even for `+` -> use wrapping/saturating operators when you intend it.
- **String is just `[]const u8`** (bytes, UTF-8 by convention); no `String` type, no built-in unicode iteration -> use `std.unicode`.
- **Std API instability**: examples from old versions break (e.g. allocator signatures, `std.ArrayList` init) -> match `zig version`.
- **`orelse`/`catch` precedence**: wrap in parens in complex expressions.
