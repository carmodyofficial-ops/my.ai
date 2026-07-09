# Roblox Networking & Replication (Expert)

## Replication model (what actually goes over the wire)
- Server is the source of truth. It replicates: instance creation/deletion, property changes, attribute changes, and physics (CFrame/velocity) for parts it owns. Replication is per-property, delta-based, batched into the outgoing packet each network step.
- Only descendants of replicated containers replicate: `Workspace`, `Players`, `ReplicatedStorage`, `Lighting`, `SoundService`, `StarterGui/Pack/Player`, `Teams`, `Chat`. **`ServerStorage`/`ServerScriptService` NEVER replicate** — put secrets there.
- Client → server replication is heavily restricted: a client can only replicate to instances it has network ownership of (its character/owned parts) plus `RemoteEvent`/`RemoteFunction` payloads. Setting a random server-owned part's `.Position` on the client is local-only and gets corrected.
- Property replication is last-write-wins per property per network step; rapid server writes to the same property in one step collapse to one replicated value. No interpolation of arbitrary properties — only physics CFrames are interpolated/smoothed client-side.
- Replication filtering: `StarterGui`/`StarterPlayerScripts` are copied per-player on spawn (not shared). `Player`-parented instances replicate only to that player + server unless in a globally-replicated container.

## StreamingEnabled (instance streaming)
- `Workspace.StreamingEnabled = true` — server streams in/out regions of `Workspace` per client by proximity to their `ReplicationFocus` (defaults to the character's `PrimaryPart`/HumanoidRootPart).
- Tunables: `StreamingTargetRadius` (~radius kept loaded, studs), `StreamingMinRadius` (never streamed out inside this), `StreamingIntegrityMode`, and per-model `ModelStreamingMode` (`Default`/`Atomic`/`Persistent`/`PersistentPerPlayer`).
- `Atomic` = model streams in as a unit (all-or-nothing) — use for anything scripts assume is whole (a rig, a machine). `Persistent` = always loaded for all players (spawn area, critical logic parts). `PersistentPerPlayer` + `Model:AddPersistentPlayer(player)` for per-player always-loaded.
- **Client scripts must handle absent instances**: use `workspace:WaitForChild` won't help if it never streams in near them. Wait on region via `player.ReplicationFocus` or `Instance.Streamed`/`workspace.PersistentLoaded`. Read parts through `:GetInstanceAddedSignal`? No — use `Model.ModelStreamingMode` = Atomic + check existence.
- Set `ReplicationFocus` manually (e.g. spectate camera, RTS/top-down) via `Player.ReplicationFocus = somePart`. There can be one focus per player.
- Streaming pause API: `player:RequestStreamAroundAsync(position)` to pre-stream before a teleport within-place.

## Network ownership (physics authority)
- `BasePart:SetNetworkOwner(player)` / `:SetNetworkOwner(nil)` (nil = server) / `:GetNetworkOwner()`. Owner simulates that assembly's physics locally and replicates results → zero-latency control for the owner, but owner is an exploiter surface.
- Default: unanchored parts near a player auto-assign to that player. The whole assembly (welded/constrained group) shares one owner; you can't split an assembly.
- **Server-own** (`SetNetworkOwner(nil)`) for: anything gameplay-critical/exploitable (moving platforms scoring position, projectiles that deal damage, physics puzzles), parts no single player should control, competitive hitboxes. Cost: server simulates + network latency on the owner's inputs.
- **Client-own** for: the player's own character (default), thrown objects they interact with, vehicles they drive (`SetNetworkOwner(driver)` on the seat assembly) — smooth for them.
- `:SetNetworkOwnershipAuto()` re-enables automatic assignment. `:GetNetworkOwnershipAuto()` checks. Anchored parts have no owner (server-simulated implicitly).
- Exploiters can teleport/speed parts they own — never trust owned-part CFrame for anti-cheat; re-validate server-side with sanity bounds + speed checks.

## RemoteEvent vs RemoteFunction vs UnreliableRemoteEvent
- **RemoteEvent** `:FireServer/:FireClient/:FireAllClients` — one-way, reliable, ordered per-remote. Default choice.
- **UnreliableRemoteEvent** — one-way, **unreliable + unordered**, no delivery guarantee, lower overhead, ~900-byte payload cap per fire (it drops/doesn't fragment large ones the same way). Use for high-frequency ephemeral data where the latest supersedes the old: positions, ragdoll sync, VFX triggers, cosmetic aim. Never for currency/state that must arrive.
- **RemoteFunction** — request/response, yields the caller. `:InvokeServer` (client waits) is fine-ish; **`:InvokeClient` is dangerous** — an exploiting client can yield forever, hanging the calling server thread, or error. Never `InvokeClient` for gameplay; use RemoteEvent + reply RemoteEvent.
- Ordering: reliable remotes preserve order **only relative to themselves and to property replication issued in the same step**. Two different RemoteEvents have no cross-ordering guarantee. If A must precede B, send both in one remote payload.
- Yield risk: a `RemoteEvent.OnServerEvent` handler that yields (`:WaitForChild`, DataStore) processes events serially per connection thread but each fire spawns its own coroutine — reentrancy means don't assume a debounce set/clear across a yield is atomic; guard with a per-player flag set BEFORE the yield.

```lua
-- Server: rate-limit + validate every remote
local last = {} -- [player] = tick
remote.OnServerEvent:Connect(function(plr, action, payload)
    local t = os.clock()
    if last[plr] and t - last[plr] < 0.05 then return end -- 20/s cap
    last[plr] = t
    if typeof(action) ~= "string" then return end
    -- ...validate payload shape/bounds before applying...
end)
```

## Batching, throttling, bandwidth budgets
- Each `:FireServer`/`:FireClient` has fixed per-message overhead (remote id + framing, tens of bytes) on top of payload. **50 fires/frame >> 1 fire with a 50-entry table.** Aggregate.
- Accumulate events, flush once per `Heartbeat` (or every N frames) as a single table payload. For per-player differing data, build one table per player and `FireClient` once each.
- Measure with `Stats`: `game:GetService("Stats"):GetTotalMemoryUsageMb()`, `Stats.DataSendKbps`, `Stats.DataReceiveKbps`, `Stats.Network.ServerStatsItem["Data Ping"]`. Client: `Stats.Network` tree, or Developer Console (F9) → Network. Budget target: keep per-client receive well under ~50 KB/s sustained; spikes cause rubber-banding.
- `ReplicationFocus` + StreamingEnabled cut baseline replication bandwidth massively vs sending the whole map.
- Attributes replicate cheaply and are typed (bool/number/string/Vector3/etc.) — prefer over hidden `IntValue`/`StringValue` object trees (each Value object is an instance = replication + memory).

## Client prediction & server reconciliation (movement)
- Pattern for responsive custom movement/abilities without cheat exposure:
  1. Client applies input immediately (predicts), tags each input with a sequence number, stores it in a pending buffer.
  2. Client sends `{seq, input, dt}` to server (UnreliableRemoteEvent for streams).
  3. Server simulates authoritatively, replies with authoritative state + last-processed `seq`.
  4. Client drops acknowledged inputs, **re-applies** unacknowledged ones on top of the server state (reconciliation). If server pos ≈ predicted, no visible correction; if it diverges (cheat/lag), client snaps/smooths to authoritative.
- Interpolate other players: buffer their state ~100 ms, render in the past for smooth motion (entity interpolation). Never extrapolate far — clamp.
- Roblox already does this for default Humanoid physics (character is client-owned). Custom prediction matters when you replace default control (custom controllers, first-person shooters, `Humanoid` off).

## Custom replication patterns
- **Replicated state module**: server holds authoritative state table, replicates diffs via one RemoteEvent (`{path, value}` or full snapshot on join, deltas after). Libraries: Roblox's `ReplicaService`/`Replica`, `BridgeNet2` (remote multiplexing/batching), `ByteNet`/`Blink`/`Zap` (buffer serialization — pack numbers into `buffer` for 5-10× smaller payloads than tables).
- `buffer` serialization: `buffer.create`, `buffer.writeu8/writef32/...` — send a `buffer` through a RemoteEvent (it's a supported type) instead of verbose tables. Huge for position streams.
- Interest management: only replicate an entity's state to players who can see/care (spatial hash by region) — mirrors StreamingEnabled for your custom data.

## Remote security boundary
- Everything a client can see is extractable: instances in replicated containers, module source in `ReplicatedStorage`, remote names/args. Exploiters can fire any remote with any args at any rate.
- **The remote handler is the trust boundary.** Validate: arg types (`typeof`), value bounds/enums, ownership (does this player own/control the target?), rate (debounce), and game-state legality (is the action allowed now?). Missing any one = exploit.
- Don't ship secret logic/data client-side. Loot tables, drop rates, hidden map data in `ReplicatedStorage` are readable — keep authoritative rolls server-side; client sends intent only.

## Gotchas -> Fix
- **Client sets a server-owned part's position, "works" locally, snaps back**: no network ownership. Fix: `SetNetworkOwner(player)` if it's legitimately theirs, else do it server-side; don't fight the reconciler.
- **Two RemoteEvents arrive out of expected order**: no cross-remote ordering. Fix: combine dependent data into one remote payload, or include a seq/version.
- **UnreliableRemoteEvent used for currency/inventory → occasional lost update**: no delivery guarantee. Fix: reliable RemoteEvent for anything that must arrive; Unreliable only for latest-wins ephemeral streams.
- **Bandwidth blows up with players**: N× small `:FireClient` per frame per player. Fix: batch per player into one table/`buffer`, throttle to Heartbeat, measure with `Stats.DataSendKbps`.
- **StreamingEnabled: client script errors "attempt to index nil"**: instance streamed out / never streamed in near the player. Fix: `ModelStreamingMode=Atomic` for rigs, `Persistent` for critical parts, and code defensively (existence checks, `Streamed` signals) — never assume a distant part exists client-side.
- **InvokeClient hangs the server**: exploiter yields the invoke. Fix: never `RemoteFunction:InvokeClient` for gameplay; use RemoteEvent + timeout on a reply.
- **Debounce bypassed via reentrancy**: flag cleared after a yield, second fire slips in. Fix: set the per-player guard BEFORE any yield; clear in the same coroutine after.
- **Anti-cheat trusts owned-part CFrame / Humanoid position**: client owns it, can lie. Fix: server-side sanity (max speed, world bounds, line-of-sight), or server-own critical parts.
- **Sensitive data readable in ReplicatedStorage**: drop rates, answer keys, admin lists. Fix: move to `ServerStorage`/`ServerScriptService`; only server rolls/decides.
- **Attributes vs Value objects for many fields**: dozens of `Value` instances = replication + memory + churn. Fix: attributes (typed, cheap) or one replicated state table.
- **Physics jitter on shared assembly**: tried to split ownership within a welded group. Fix: one owner per assembly; break constraints if independent control is needed.
- **`FireAllClients` with per-player data**: sends everyone everyone's data (waste + leak). Fix: `FireClient` per player with only their slice.
- **Property spam replication**: writing a part property every RenderStepped server-side. Fix: only write on change, throttle, or use physics ownership so it replicates as motion.
