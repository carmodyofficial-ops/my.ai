# Roblox Luau Deep (typing, buffers, native, perf)

## Strict typed Luau mastery
- Header `--!strict` (full inference + errors), `--!nonstrict` (errors only on annotated), `--!nocheck` (off). Strict is per-file.
- **Generics** on functions and type aliases:
```lua
--!strict
export type Result<T, E = string> = { ok: true, value: T } | { ok: false, err: E }
local function map<T, U>(t: { T }, f: (T) -> U): { U }
    local o = table.create(#t)
    for i, v in t do o[i] = f(v) end
    return o
end
```
- **Union / intersection / singleton**: `type State = "idle" | "run" | "dead"` (singleton strings narrow via `if`); intersection `type C = A & B` merges fields. Optional field `field: number?` == `number | nil`.
- **Type functions** (new): compute types at analysis time:
```lua
type function MakeReadonly(t)
    local nt = types.newtable()
    for k, v in t:properties() do nt:setproperty(k, v.read) end
    return nt
end
```
- `typeof(x)` (runtime, returns `"Instance"`, `"Vector3"`, etc.) vs `type(x)` (Luau primitives only — Instances/Vector3 all report `"userdata"`). Use `typeof` for Roblox objects.
- **Type of instance shape**: `typeof(setmetatable(...))` captures class type; `local x = Instance.new("Part") :: Part` narrows Instance. `x:IsA("BasePart")` narrows in a following block.
- Export shared types from one ModuleScript; `require` and reference `Types.Foo`. Prefer `type` aliases over inline shapes everywhere.

## When the analyzer lies + escape hatches
- Boundaries are `any`: `RemoteEvent.OnServerEvent` args, `DataStore:GetAsync`, `HttpService:JSONDecode`, `Instance:FindFirstChild` (returns `Instance?`). Strict gives false comfort — runtime-validate at the boundary before casting.
- Casts: `expr :: Type` (checked-ish downcast), `expr :: any` (nuclear escape — kills checking downstream; isolate to one line). `(x :: any) :: Target` forces an unrelated cast.
- `FindFirstChild` returns `Instance?`; guard `if part and part:IsA("BasePart") then` — the `:IsA` refines the type, not just runtime.
- Analyzer can't see `:WaitForChild` result class — annotate: `local gui = plr:WaitForChild("PlayerGui") :: PlayerGui`.
- `assert(x)` narrows `x` from `T?` to `T` for the analyzer. Use over `:: any` when you truly expect non-nil.

## Performance idioms (hot paths)
- **Preallocate**: `table.create(n)` / `table.create(n, v)` avoids rehash growth. In hot loops avoid `table.insert` — use `t[#t+1] = v` or an explicit running index (insert has call overhead + length recompute).
- **Numeric `for`** over `ipairs`/`pairs` when you have contiguous arrays and an index; generalized `for i, v in t` (Luau's `__iter`) is fine and fast for iteration, but numeric index avoids the iterator when you already track `i`.
- **Avoid per-frame allocation** in `RenderStepped`/`Heartbeat`: no table/closure/Vector3 churn each frame — reuse buffers, hoist constants, pool objects. GC pressure = frame spikes.
- `string.format` and `..` concat allocate — cache formatted strings; don't build strings every frame for UI (only on change). Use `table.concat` for many pieces, not repeated `..`.
- **`__index` chains cost**: deep inheritance means each miss walks the metatable chain. In hot code, flatten (copy methods down) or cache the method locally: `local dmg = self.damage` before a tight loop.
- Localize globals/service lookups: `local v3 = Vector3.new` hoisted beats repeated global reads (Luau resolves locals via register, globals via hash). Cache `workspace`, math funcs.
- `math.floor`/bit ops are cheap; `%` and `/` fine; avoid `math.huge`/NaN leaking into comparisons.
- Vector3/CFrame are immutable value types — arithmetic allocates new ones; batch and minimize creations in loops.

## The `buffer` type (binary data)
- `buffer` = resizable raw byte array for compact binary + bit-level packing. Great for network payloads (send one buffer over a remote instead of a big table), custom serialization, saving compact data.
```lua
local b = buffer.create(8)
buffer.writeu16(b, 0, 1000)     -- offset 0, u16
buffer.writef32(b, 2, 3.5)      -- offset 2, f32
local hp = buffer.readu16(b, 0)
```
- API: `create(size)`, `fromstring`/`tostring`, `len`, `copy`, `fill`, and typed read/write: `u8 i8 u16 i16 u32 i32 f32 f64` + `readstring/writestring`. Offsets are byte-based; out-of-bounds errors.
- Massively smaller than tables for arrays of numbers; buffers replicate over remotes efficiently and are the idiom for high-frequency state (positions packed as f32s).
- Bit ops: `bit32.band/bor/bxor/bnot/lshift/rshift/extract/replace` for flags/masks packed into a u32.

## Native code generation
- **`--!native`** at file top opts the whole script into native codegen (server & most client Scripts; compiled to machine code, big win for math-heavy Luau). **`--!optimize 2`** requests max optimization level.
- Qualifies best: numeric/vector-heavy pure Luau (physics, procgen, pathfinding, tight loops). Poor fit: code dominated by Instance API / yielding / DataModel calls (native can't accelerate the C++ boundary crossings).
- Native has limits: very large functions may fall back to interpreter; it increases memory. Measure with MicroProfiler — don't blanket-apply. `debug.profilebegin("tag")`/`debug.profileend()` around candidates.
- `--!optimize 2` alone (without native) still enables aggressive interpreter optimizations.

## OOP + metatable performance
```lua
local Vec = {}
Vec.__index = Vec
export type Vec = typeof(setmetatable({} :: { x: number, y: number }, Vec))
function Vec.new(x: number, y: number): Vec
    return setmetatable({ x = x, y = y }, Vec)
end
function Vec.add(self: Vec, o: Vec): Vec return Vec.new(self.x+o.x, self.y+o.y) end
```
- `Class.__index = Class` (a table) makes instances fall back to methods. Method call `obj:add(o)` reads `add` via one `__index` hop — cheap but nonzero; in hottest loops prefer plain functions over method dispatch, or hoist the method.
- **Closures vs methods cost**: a closure capturing upvalues allocates a new function object per creation (each `.new` making per-instance closures = N allocations + captured-var memory). Methods on a shared metatable allocate ONCE. Prefer metatable methods over per-instance closures for many objects.
- Avoid `__index` as a *function* unless you need computed defaults (it runs on every miss). Metamethods to know: `__index __newindex __eq __lt __le __call __tostring __len __iter`.

## Closures, upvalues, memory
- **Upvalue capture pitfall**: a closure captures the *variable*, not a snapshot — loop closures over a shared upvalue all see the final value unless the loop var is fresh per iteration (Luau's `for` gives a fresh binding per iteration, so `for i` closures capture distinct `i`; a manually mutated `local` outside does not). Verify before relying on it.
- Closures pin their upvalues alive (memory): a long-lived connection callback capturing a big table keeps that table un-GC'd. Null out captured refs or use a Janitor/weak refs.
- **Weak tables**: `setmetatable(cache, { __mode = "k" })` (or `"v"`/`"kv"`) lets GC collect keys/values with no other refs — good for caches keyed by Instances so leaving players/parts get collected.
- Reuse tables (object pooling) instead of allocating; `table.clear(t)` empties without freeing capacity for reuse.
- Connections are the #1 leak: an un-`:Disconnect()`ed connection keeps the closure + captured instances alive. Track and clean (Trove/Maid/Janitor).

## Iteration, coroutines, error handling
- **Generalized `for i, v in t`** uses Luau's `__iter` metamethod (define `__iter` on a class to make instances iterable). It's the idiomatic fast path — beats `pairs`/`ipairs` (which still work; `ipairs` stops at first `nil`, `pairs` is unordered incl. hash part).
- **`pcall` cost**: cheap enough for boundaries (DataStore, remotes, `require`) but don't wrap hot inner loops in `pcall` — the protected-call setup adds overhead per call. Validate inputs so the loop can't error, wrap the whole loop once.
- **Error objects**: Luau `error(obj, level)` can throw tables (not just strings) — `pcall` returns `(false, obj)`; carry structured errors (`{code=..., msg=...}`) instead of parsing strings. `level` controls where the error is reported (`2` blames the caller).
- **Coroutines**: `coroutine.create/resume/yield/wrap`; a yielded coroutine holds its stack + upvalues alive (memory). Prefer `task.spawn`/`task.defer` (they resume on the scheduler and surface errors) over raw `coroutine` for Roblox threads; raw `coroutine.wrap` swallows errors silently.
- **String interning**: identical short strings are interned — comparison is pointer-equality (fast); building many unique strings defeats it and pressures GC.

## Gotchas -> Fix
- **`--!strict` false comfort at boundaries** → remote/DataStore/JSON payloads are `any`. Fix: runtime-typecheck (e.g. `t` library) before casting; treat boundary as untyped.
- **`type()` on Roblox objects** → Vector3/Instance all report `"userdata"`. Fix: use `typeof(x)`.
- **`table.insert` in a hot loop** → call + length overhead per element. Fix: `t[#t+1]=v` or a tracked index; `table.create(n)` to preallocate.
- **Per-instance closures for methods** → N function allocations + upvalue memory. Fix: shared metatable methods; closures only when you need captured state.
- **Blanket `--!native`** → no gain (or memory cost) on Instance/yield-heavy code; huge functions fall back. Fix: apply to math-heavy pure Luau, measure MicroProfiler.
- **`:: any` spreading** → one cast poisons downstream inference. Fix: cast to the precise type, isolate `any` to a single validated line.
- **Deep `__index` inheritance in tight loop** → chain walks each miss. Fix: hoist the method to a local, or flatten the hierarchy.
- **String building every frame** → allocations + GC spikes. Fix: format only on value change; cache; `table.concat` for batches.
- **Closure captures big table forever** → leak via long-lived connection. Fix: disconnect (Janitor), null captured refs, weak tables for Instance-keyed caches.
- **`__index` set to a function accidentally** → runs on every field miss, can loop. Fix: `Class.__index = Class` (table) unless you deliberately compute.
- **Reading `FindFirstChild` result as non-nil** → it's `Instance?`; strict flags it, runtime nil-errors. Fix: guard/`assert`/`WaitForChild` with class annotation.
- **NaN slipping through `n > max`** → NaN comparisons are false. Fix: `n ~= n` check for NaN, `math.abs(n)==math.huge` for inf.
- **`buffer` offset out of bounds** → hard error. Fix: size with `buffer.create` for total bytes; track offsets; use `buffer.len`.
