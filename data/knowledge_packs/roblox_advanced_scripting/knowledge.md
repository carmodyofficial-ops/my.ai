# Roblox Advanced Scripting (Luau)
## Strict typed Luau
- File header `--!strict` (or `--!nonstrict`). Enables type checking; `--!native` opts a script into native codegen.
- Type exports + generics:
```lua
--!strict
export type Result<T> = { ok: true, value: T } | { ok: false, err: string }
local function map<T, U>(t: {T}, f: (T) -> U): {U}
    local out = {}
    for i, v in t do out[i] = f(v) end
    return out
end
```
- Prefer `type` aliases over sprinkling shapes. Union/singleton types (`"idle" | "run"`) model states. `typeof(x)` for runtime; type functions can't. Cast with `x :: SomeType`; escape hatch `x :: any` (avoid).
## OOP with metatables
```lua
local Animal = {}
Animal.__index = Animal
export type Animal = typeof(setmetatable({} :: { name: string, hp: number }, Animal))
function Animal.new(name: string): Animal
    return setmetatable({ name = name, hp = 100 }, Animal)
end
function Animal.damage(self: Animal, n: number) self.hp -= n end
```
- `__index = Class` makes instances fall back to methods. Inheritance: `setmetatable(Sub, {__index = Base})`. Use `self` explicitly for typed methods. Metamethods: `__index`, `__newindex`, `__eq`, `__tostring`, `__lt`, `__call`.
## Module architecture
- **Service/Controller** (Knit): Services run server-side (authoritative, expose remotes via `Client` table); Controllers run client-side. Knit auto-wires networking; `Knit.Start():andThen(...)`. Lifecycle `:KnitInit` then `:KnitStart`.
- **roblox-ts** — write TypeScript, compiles to Luau. `@rbxts/services`, Flamework DI. Real generics/interfaces, npm ecosystem.
- Single-responsibility ModuleScripts required by a bootstrapper; avoid circular `require` (split shared types out).
## Advanced DataStore
- Always `UpdateAsync(key, transform)` not Get+Set (atomic, avoids lost writes). Return `nil` from transform to abort.
- **Session locking** (ProfileService pattern): store a lock `{jobId, timestamp}` in the profile; on load, steal only if stale. Prevents item-dupe across servers on teleport/rejoin.
- **ProfileService** — session-locked profiles, auto-retry, `:Reconcile()` to fill new fields, `:ListenToRelease()`. Or **DataStore2** for versioned backups.
- **OrderedDataStore** — leaderboards; `GetSortedAsync(false, 100)` pages. Separate from main data.
- Throttling: budget via `DataStoreService:GetRequestBudgetForRequestType()`. Retry with exponential backoff on `pcall` failure; never spin without backoff. Batch player data into one key, not many.
## Networking & authority
- Server is authoritative — NEVER trust client input; validate on server (position, rate, ownership). Client predicts, server reconciles.
- **RemoteEvent** batching: aggregate many small fires into one per-frame payload; a table beats 50 fires. **UnreliableRemoteEvent** for high-frequency non-critical (positions, VFX) — no ordering/delivery guarantee, lower cost.
- RemoteFunction blocks + can be exploited (client can yield forever) — prefer RemoteEvent + callback. Rate-limit remotes server-side (debounce per player).
- Replication: use Attributes + `StreamingEnabled` for spatial streaming; `Instance:SetAttribute` replicates cheaply.
## Parallel Luau
- Actors isolate state; scripts under an `Actor` run on separate threads.
- `task.desynchronize()` enters parallel phase (read-only to most of DataModel, no instance mutation); `task.synchronize()` returns to serial to mutate.
```lua
local function work()
    task.desynchronize()      -- parallel: heavy math, raycasts (read)
    local hit = workspace:Raycast(o, d)
    task.synchronize()        -- serial: safe to mutate
    part.Position = hit.Position
end
```
- Cross-actor comms via `SharedTable` or `BindableEvent`/messaging. Good for pathfinding, procedural gen, many raycasts.
## Performance & memory
- **MicroProfiler** (Ctrl+F6) + `debug.profilebegin("tag")`/`debug.profileend()`. Script Performance & MemoryStore tabs; `game:GetService("Stats")`.
- Reuse tables/parts (object pooling); avoid per-frame allocations in `RenderStepped`. Disconnect connections + `Debris` / `:Destroy()` to prevent leaks (dangling connections pin instances).
- `StreamingEnabled` for large maps; `CollectionService` tags over deep instance trees.
## State machines & Promises
- FSM: map `{ [state] = { [event] = nextState } }` + `onEnter`/`onExit`. Or roblox-lua-promise `Promise.new`, `:andThen`, `:catch`, `Promise.all`, `:timeout` — model async DataStore/HTTP without callback nesting.
## Signals, connections, cleanup
- `Instance.Changed` / `GetPropertyChangedSignal(prop)` fire on replicated changes. `:GetAttributeChangedSignal(name)` for attributes.
- **Janitor/Maid/Trove** pattern — register connections, instances, and cleanup fns; `janitor:Cleanup()` disconnects/destroys all at once. Prevents the #1 leak (orphaned connections).
```lua
local Janitor = require(Packages.Janitor).new()
Janitor:Add(part.Touched:Connect(onTouch), "Disconnect")
Janitor:Add(part, "Destroy")
-- later:
Janitor:Cleanup()
```
- `task.spawn`/`task.defer`/`task.delay` over deprecated `spawn`/`wait` (wait throttles, drifts). `task.wait()` returns delta, resumes next Heartbeat.

## Client-server patterns
- Sanity-check chain: validate arg types → check ownership/permission → rate-limit (per-player debounce) → apply → replicate result. Do all four, always.
- Anti-exploit: no gameplay logic client-side that awards value; client sends *intent*, server decides outcome. Obfuscation is not security.
- Use **Attributes** + **CollectionService tags** for data-driven, replicated state instead of hidden `Value` objects or `_G`.

## Tooling
- **Rojo** — sync filesystem ↔ Studio; `default.project.json` maps dirs to services; enables Git + external editors.
- **Wally** — package manager (`wally.toml`, `Packages/`). **Aftman/Rokit** — toolchain manager pins Rojo/Wally/selene versions. **selene** lint, **StyLua** format, **Luau LSP**.
- **TestEZ** for BDD unit tests; run headless via `run-in-roblox` / open-cloud Luau execution in CI.
- Package via Wally: pin exact versions in `wally.toml`, commit lockfile, `wally install` populates `Packages/` (git-ignored).

## Gotchas -> Fix
- **Data loss / item dupe**: two servers write same key (teleport, fast rejoin). Fix: session locking (ProfileService); `UpdateAsync`, never Get+Set.
- **`self` is nil / "expected 1 got 0"**: called `obj.method()` with `.` not `:`. Fix: `:` for methods, or take explicit `self` param and be consistent.
- **`__index` set to a function unintentionally**: fallback loops or wrong lookups. Fix: `Class.__index = Class` (a table); use a function only for computed defaults.
- **DataStore throttled / errors dropped**: no `pcall`, no retry, hammering budget. Fix: wrap in `pcall`, exponential backoff, check `GetRequestBudgetForRequestType`, batch keys.
- **Exploiters trust client**: setting stats/positions via remotes. Fix: server-authoritative validation, sanity-check every remote arg, rate-limit.
- **Parallel Luau writes crash**: mutating instances inside `task.desynchronize()`. Fix: only read in parallel; `task.synchronize()` before any DataModel write.
- **Memory leak / rising instance count**: connections never `:Disconnect()`ed keep objects alive. Fix: track and disconnect; use `Trove`/`Maid`/`Janitor` to bulk-clean.
- **`--!strict` false comfort at boundaries**: remote payloads, `DataStore` reads, `JSONDecode` are `any`. Fix: validate/typecheck at the boundary (e.g. `t` runtime typechecker) before trusting types.
- **RemoteFunction hang**: exploiter never returns from client invoke, yielding server. Fix: RemoteEvent one-way; never invoke client with RemoteFunction for gameplay.
- **Circular require deadlock**: ModuleA requires ModuleB requires ModuleA. Fix: extract shared types/consts to a third module; lazy-require inside functions.
- **Frame spikes**: heavy work in `RenderStepped`/`Heartbeat` every frame. Fix: throttle, offload to Actor, pool objects, `debug.profilebegin` to find the tag.
