# Roblox Performance Optimization (Expert)

## MicroProfiler (the primary tool)
- Toggle: `Ctrl+F6` (or Ctrl+Alt+F6). `Ctrl+P` pauses. It shows per-frame CPU time split into labeled scopes on the timeline. **Runs on both client and server** — in Studio switch the target; in live games use the server MicroProfiler via `game:GetService("Stats")` + `Settings` or the "server microprofiler" API.
- Frame budget: **60 FPS = 16.67 ms/frame**; 30 FPS = 33 ms. Anything a scope eats above a few ms per frame is a lead. Look for wide bars in `RunService.Heartbeat`, `RenderJob`, `Physics`, `Signals`.
- Custom labels: `debug.profilebegin("MySystem")` … `debug.profileend()` (must be balanced, same frame). `debug.setmemorycategory("MySystem")` tags memory to your category in the Developer Console.
- Server dump: `Stats` + MicroProfiler "dump" — capture N frames to a file, open with the standalone/web MicroProfiler viewer for flame-graph analysis offline. Trigger programmatically for a live server via the profiler dump APIs; grab during the spike.
- Methodology: reproduce the spike → dump → find the widest scope → attribute to a script/system → fix → re-measure. Never optimize by guess; the profiler names the culprit.

## Memory (leaks are the silent killer)
- Developer Console (`F9`) → **Memory** tab: per-category MB (PlaceMemory, Instances, LuaHeap, GraphicsTexture, etc.). Watch it climb over a session — flat = healthy, monotonically rising = leak.
- `Stats:GetTotalMemoryUsageMb()` and `Stats:GetMemoryUsageMbForTag(Enum.DeveloperMemoryTag.X)` for programmatic watching/alerting.
- **#1 leak: connections not disconnected.** A live `Connection` keeps its closure + upvalues + the signal's instance alive. `part.Touched:Connect(fn)` where `fn` captures a big table → that table never GCs while connected. Fix: track every connection, `:Disconnect()` on teardown; use Trove/Maid/Janitor.
- **#2 leak: instances not destroyed / still parented.** Removed from view ≠ collected. Must `:Destroy()` (also disconnects its events, sets parent locked). Setting `.Parent = nil` alone leaks if a reference/connection remains.
- Tables that only grow: caches keyed by player/instance never pruned. Fix: prune on `PlayerRemoving`/`AncestryChanged`, or use **weak tables** `setmetatable(cache, {__mode = "k"})` (weak keys) so entries GC when the key instance is collected — but weak-table entries vanish unpredictably; only for pure caches, never for state.
- Luau GC is incremental mark-sweep; you rarely call it manually. A rising `LuaHeap` with stable logic = retained references (closures/connections/tables), not GC lag.
- Event vs closure retention: `RBXScriptConnection` isn't GC'd by dropping the variable — it's held by the signal. Explicit `:Disconnect()` required.

## Instance count & streaming tuning
- Instance count is a top perf/memory axis. Check Developer Console → Instances, or `#workspace:GetDescendants()`. Tens of thousands of parts = replication + physics + render + memory pressure.
- Reduce: merge static geometry into fewer `MeshPart`s (union sparingly — CSG is heavy), use `SurfaceAppearance`/textures instead of many small parts, delete decorative parts far from play, avoid deep `Folder`/`Value` trees.
- `StreamingEnabled` for large maps (see replication pack): cuts loaded instance count per client to the region around their `ReplicationFocus`. Tune `StreamingTargetRadius`/`StreamingMinRadius`; mark critical models `Persistent`, whole rigs `Atomic`.
- Anchor everything static (`Anchored = true`) — unanchored parts get physics assemblies + network ownership overhead even at rest.

## Script performance
- **Avoid per-frame waste.** Don't do work every `RenderStepped`/`Heartbeat` that could be event-driven. Prefer `GetPropertyChangedSignal`/`:GetAttributeChangedSignal`/`.Changed` (event) over polling a value each frame.
- Connect once, not in a loop. Never `Connect` inside another frequently-firing handler (connection leak + duplicate work).
- `Instance:GetChildren()`/`GetDescendants()` allocate a new table every call and are O(n) — cache the result, don't call in a hot loop. Iterate `workspace:GetDescendants()` once at init, not per frame.
- Table reuse / object pooling: pre-allocate parts/tables, recycle instead of `Instance.new`/`Destroy` churn (allocation + GC pressure + replication). Pool bullets/effects/UI rows.
- Avoid table allocations in hot paths (new `{}`/`Vector3.new` each frame → GC churn). Reuse buffers; mutate in place. `Vector3`/`CFrame` are immutable values (cheap, no GC individually) but constructing thousands/frame adds up.
- Use `--!native` on CPU-heavy compute modules (native codegen) and `--!strict` (lets the compiler optimize; catches nils). `table.create(n)` to pre-size arrays; `table.clear` to reuse.
- `task.wait()`/`RunService.Heartbeat:Wait()` over deprecated `wait()` (throttled, min ~30ms, drifts). Prefer `task.defer`/`task.delay` over `spawn`.
- String concat in loops → `table.concat`. Repeated `FindFirstChild` → cache the ref once (with existence guard for streaming).

## Parallel Luau (offload heavy CPU)
- Put scripts under an **`Actor`** instance to enable parallel execution. Each Actor is an isolated execution context; scripts in different Actors can run on different cores.
- `task.desynchronize()` → parallel phase: read-only to most of the DataModel, **no instance mutation, no creating/parenting/destroying**. Do heavy math, `workspace:Raycast` (read), `Region3`, pathfinding cost calc here.
- `task.synchronize()` → back to serial phase: safe to mutate instances/properties. Batch your writes here.
```lua
-- Script under an Actor
local RunService = game:GetService("RunService")
RunService.Heartbeat:ConnectParallel(function() -- runs in parallel phase
    local results = {}
    for i, ray in rays do results[i] = workspace:Raycast(ray.o, ray.d) end
    task.synchronize()            -- serial
    applyResults(results)         -- safe to mutate now
end)
```
- Cross-actor comms: **`SharedTable`** (thread-safe shared data, use for large parallel datasets) or `BindableEvent`/`Actor:SendMessage`+`BindToMessage`. Don't pass instances between actors expecting shared mutation.
- Good fits: raycasting swarms, procedural generation, pathfinding, mesh/voxel work, AI perception. Bad fits: anything mostly touching instances (sync overhead dominates) or trivial work (Actor/sync cost > gain).

## Rendering budget
- Target scopes in MicroProfiler `Render`: draw calls, `Prepare`, `Perform`. **Draw calls** ≈ number of unique render batches; fewer = better. Same mesh + same material/texture batches together.
- Parts vs MeshParts: many primitive parts each cost; a single `MeshPart` with baked geometry + one texture batches into far fewer draw calls. Reuse the same `MeshId`/`SurfaceAppearance` so instances batch.
- **Overdraw** from transparency: overlapping semi-transparent surfaces (particles, glass, foliage cards) re-shade the same pixels repeatedly → GPU-bound stalls. Limit particle `Rate`/count, avoid stacked transparent parts, cap `ParticleEmitter` overdraw.
- Lighting tech cost: `Voxel` (cheapest) < `ShadowMap` < `Future` (`FutureIsBright`, best quality, most expensive — per-light shadows, PBR). Fewer shadow-casting lights; `Light.Shadows=false` where not needed. `GlobalShadows`, lower `Technology` on low-end.
- PBR/`SurfaceAppearance` (albedo/normal/metalness/roughness maps) looks great but adds texture memory + sampling — budget `GraphicsTexture` memory; compress textures, reuse maps.
- LOD: `MeshPart.RenderFidelity = Enum.RenderFidelity.Automatic` (distance LOD). `Precise` only when needed. Distant detail → remove or stream out.
- Cap effects: `PostEffect`s (Blur/Bloom/DOF/ColorCorrection) are full-screen passes; each costs. `QualityLevel` scaling for low-end devices.

## Physics
- Physics runs on `Stepped`; cost scales with active (awake) assemblies. Sleeping/anchored parts are cheap. `Anchored=true` for static.
- **`CanTouch` and `CanQuery`**: set `false` on parts that don't need `.Touched` events or raycast/`GetPartBoundsInBox` hits — removes them from the spatial query broadphase (big win with many parts). `CanCollide=false` alone still incurs touch/query cost.
- `Touched` events are expensive + spammy; prefer `GetPartsInPart`/`Workspace:GetPartBoundsInBox`/raycasts on demand, or `CanTouch=false` + explicit region checks.
- Constraints/ragdolls: many active constraints = physics cost + network. Despawn ragdolls quickly, cap simultaneous.
- Network/simulation: unowned unanchored parts near players auto-assign ownership (client sim + replication). Server-own critical physics (cost) vs client-own for smoothness. `CollisionGroups` (`PhysicsService`) to skip needless collision pair checks.
- `workspace.PhysicsSteppingMethod`, `MaxParts`/mechanism throttling; keep `Humanoid` count down (each is expensive — state machine + physics). Use `Humanoid:ChangeState`/disable states, or no Humanoid for non-character rigs.

## Asset streaming & preloading
- `ContentProvider:PreloadAsync({instances/ids})` on a loading screen to avoid in-game hitches from first-use texture/mesh/sound decode. Don't preload everything (memory) — preload what the player sees first.
- Textures/meshes load lazily on first render; the hitch is decode + upload. Preload spawn-area assets; let far assets lazy-load.
- `Sound.PreloadAsync`, image `ContentId` warms. Audio: stream long tracks, preload short SFX.

## Profiling methodology
1. Reproduce reliably. 2. Is it CPU (frame time high in MicroProfiler) or GPU (frame time high but CPU idle → look at Render/draw calls/overdraw) or memory (rising heap/instances)? 3. MicroProfiler dump the spike; find widest scope. 4. Attribute → one system/script. 5. Fix the algorithm (event vs poll, batch, pool, parallelize), not micro-syntax. 6. Re-measure; confirm the scope shrank. 7. Watch memory over a full session for leaks (F9 Memory flat = good).

## Gotchas -> Fix
- **Memory climbs all session → OOM/crash**: undisconnected connections pinning closures/instances. Fix: Trove/Maid; `:Disconnect()` + `:Destroy()` on teardown; audit `:Connect` sites.
- **`GetDescendants()`/`GetChildren()` in a hot loop**: O(n) + fresh table each call. Fix: cache once at init; update via `ChildAdded`/`ChildRemoved`.
- **Polling a value every frame**: wasted CPU. Fix: `GetPropertyChangedSignal`/attribute-changed/`.Changed` event-driven.
- **Instance churn (`Instance.new`/`Destroy` per shot/effect)**: allocation + GC + replication spikes. Fix: object pool; recycle.
- **Parallel Luau crash "cannot mutate in parallel"**: writing instances inside `desynchronize`/`ConnectParallel`. Fix: read in parallel, `task.synchronize()` before any write.
- **GPU-bound but CPU looks fine**: high draw calls / transparency overdraw / Future lighting on low-end. Fix: batch meshes (shared MeshId+texture), cut transparent overlap/particles, lower lighting `Technology`, fewer shadow lights.
- **`Touched` lag with many parts**: broadphase + event spam. Fix: `CanTouch=false`/`CanQuery=false` where unused; explicit `GetPartBoundsInBox`/raycast on demand; CollisionGroups.
- **Stutter on first encounter with an asset**: lazy texture/mesh decode. Fix: `ContentProvider:PreloadAsync` on the loading screen for first-seen assets.
- **Weak table lost my state**: used `__mode` for authoritative data → GC'd it. Fix: weak tables only for reconstructible caches; never for state; prune real state on player leave.
- **Studio-only profiling misses live spikes**: server load/latency differs. Fix: server MicroProfiler dump on the live game; measure with real player counts.
- **High instance count from Value objects/Folders**: replication + memory. Fix: attributes/one state table; flatten trees.
- **Everything unanchored**: needless physics assemblies + ownership. Fix: `Anchored=true` for static geometry.
- **`wait()`/`spawn()` drift & throttle**: deprecated, min delay, error swallowing. Fix: `task.wait`/`task.spawn`/`task.defer`/`task.delay`.
