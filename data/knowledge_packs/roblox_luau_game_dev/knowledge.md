# Roblox + Luau Game Dev Reference

## Luau Idioms
- `local` everything; no globals. `local Players = game:GetService("Players")`.
- Use `task.wait()`, `task.spawn()`, `task.defer()` — NEVER deprecated `wait()`/`spawn()`/`delay()`.
- Typed Luau: `local hp: number = 100`, `local function add(a: number, b: number): number`. Add `--!strict` at top.
- Method calls with `:` (`part:Destroy()`); `.` for properties/static.
- `if x then`, `if not x then`; check nil explicitly (`if inst == nil then`). `and`/`or`, no `&&`. String concat is `..`, inequality is `~=`.
- Numeric `for i = 1, 10 do`; generic `for i, v in ipairs(t)` / `for k, v in pairs(t)` (or just `for k, v in t` in modern Luau). `continue` allowed. Arrays are 1-indexed.

## Client–Server Security (CRITICAL)
- Server is authoritative. NEVER trust the client. FilteringEnabled is always on.
- Exploiters fire ANY remote with ANY args at ANY rate, read ALL client code/LocalScripts, and modify anything client-side. Assume every remote is called maliciously.
- Validate EVERY remote arg server-side: type (`typeof(x) == "number"`), NaN (`x ~= x`), range/bounds, ownership, existence (`Instance` may be nil or a foreign object), rate limit.
- Do ALL damage, economy, inventory, teleport/position-authority changes on the server. Client sends intent + renders.
```lua
local lastUse: {[Player]: number} = {}
buyRemote.OnServerEvent:Connect(function(plr, id)
	if typeof(id) ~= "number" or id ~= id or id % 1 ~= 0 then return end
	local now = os.clock()
	if lastUse[plr] and now - lastUse[plr] < 0.5 then return end -- rate limit
	lastUse[plr] = now
	-- verify price, funds, ownership from SERVER data, then grant
end)
Players.PlayerRemoving:Connect(function(plr) lastUse[plr] = nil end)
```
- Common exploit vectors -> server checks: teleport/speed hacks -> validate position deltas vs max speed on server, or make server own movement-critical outcomes; hit "anyone from anywhere" -> distance + line-of-sight + cooldown checks on the damage remote; negative/huge purchase amounts -> integer + range check; firing admin-only remotes -> check `plr` identity/role server-side, never a client-sent "isAdmin" flag; spamming remotes -> per-player token bucket/cooldown; passing another player's Instance -> verify `plr` matches the target's owner.
- Never store secrets or grant logic in ReplicatedStorage/LocalScripts — clients can read them. Server-only code in `ServerScriptService`/`ServerStorage`.

## RemoteEvent / RemoteFunction Patterns
- `RemoteEvent`: one-way (`:FireServer(args)`, `:FireClient(plr, args)`, `:FireAllClients(args)`). First param of `OnServerEvent` is ALWAYS the sending `Player` (injected, unspoofable).
- `RemoteFunction`: request->response (`:InvokeServer`). NEVER `:InvokeClient` from server / never yield the server waiting on a client — exploiter can hang or error it. Prefer two RemoteEvents.
- `UnreliableRemoteEvent`: high-frequency, loss-tolerant data (effects, non-critical position) — no ordering/delivery guarantee, ~900 byte limit.
- Keep remotes in `ReplicatedStorage`, created by the server at startup; clients `:WaitForChild("Remotes")`. One remote per concern beats one god-remote with a string command (still validate either way).
- pcall client invocations of RemoteFunction; server code that errors in a handler kills only that invocation but logs — validate first, act second.

## Services (`game:GetService`)
- `Players`: `PlayerAdded`, `player.CharacterAdded`. Handle players already present at connect time (loop `Players:GetPlayers()`).
- `RunService`: `Heartbeat` (after physics, server+client), `RenderStepped` (client pre-render only — keep cheap), `Stepped` (before physics). Use the `dt` param — never hardcode frame time.
- `ReplicatedStorage`: shared modules/remotes/assets. `ServerScriptService`/`ServerStorage`: server-only, never replicated.
- `UserInputService`/`ContextActionService`: input (client). `Debris:AddItem(part, 5)`: auto-cleanup transient instances.

## CollectionService Tags
- Tag instances in Studio or `CollectionService:AddTag(inst, "Lava")`; query `GetTagged("Lava")`.
- Pattern: behavior-per-tag with live add/remove:
```lua
local CS = game:GetService("CollectionService")
local function setup(inst) inst.Touched:Connect(onLava) end
for _, v in CS:GetTagged("Lava") do setup(v) end
CS:GetInstanceAddedSignal("Lava"):Connect(setup)
CS:GetInstanceRemovedSignal("Lava"):Connect(cleanup)
```
- Beats folder-scanning and per-instance scripts; works with streaming (handle instances appearing later).

## TweenService
- `TweenService:Create(inst, TweenInfo.new(1, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {Position = target}):Play()`.
- Tweens any tweenable property (Position, Size, Transparency, Color, CFrame). `tween.Completed:Wait()` to sequence.
- Tween on the CLIENT for visual polish (smooth for each player, offloads server). Server tweens replicate but stutter with latency.
- Overlapping tweens on the same property: the new one cancels the old. Cancel manually with `tween:Cancel()`; `:Pause()` keeps progress.

## StreamingEnabled
- `Workspace.StreamingEnabled = true`: parts stream in/out around each client by distance. Client scripts must NOT assume workspace content exists: use `:WaitForChild()`, CollectionService added-signals, or `workspace:GetPersistentLoading`-style anchors.
- Server always sees everything; only client visibility streams.
- Mark must-always-exist models `ModelStreamingMode = Persistent` (or PersistentPerPlayer via `player:AddReplicationFocus`-adjacent APIs). Set `player.ReplicationFocus` for camera-remote gameplay.

## Code Structure
- `ModuleScript` for shared/reusable logic: `return M` then `require(path)`. Cached per-context (server and client each get their own copy — module state does NOT cross the boundary).
- `BindableEvent`/`BindableFunction`: same-context signaling only (server<->server or client<->client).

## DataStore
- `DataStoreService:GetDataStore("Players")`. Wrap every call in `pcall` + retry with exponential backoff.
- Save on `PlayerRemoving` AND `game:BindToClose(fn)` (server shutdown; you get ~30 s). Never trust unsaved in-memory state.
- Use `UpdateAsync` for read-modify-write (prevents lost updates from multi-server races); `SetAsync` only for blind overwrites. Respect request budgets; batch/debounce saves (e.g., autosave every 60-120 s per player).
- Session locking (store a lock timestamp in the value, or use MemoryStoreService) prevents dupes from server-hopping.

## UI
- `ScreenGui` in `PlayerGui` (client). Size/Position via `UDim2.new(scaleX, offsetX, scaleY, offsetY)` — scale for resolution independence. Buttons: `btn.Activated:Connect(fn)` (touch + click).

## Monetization (MarketplaceService)
- GamePass: `PromptGamePassPurchase`; gate with `UserOwnsGamePassAsync(userId, id)` (pcall it).
- DevProduct: `PromptProductPurchase`; `ProcessReceipt` MUST be idempotent (record `receiptInfo.PurchaseId` in DataStore) and return `Enum.ProductPurchaseDecision.PurchaseGranted` only AFTER granting persisted.

## Gotchas -> Fix
- **Trusting client** -> validate type/range/ownership/rate server-side; client never authoritative.
- **Yielding in RemoteFunction server handler / InvokeClient** -> return fast; use RemoteEvents both ways.
- **`wait()`/`spawn()`** -> `task.wait()`/`task.spawn()`.
- **Un-pcall'd DataStore** -> pcall + retry/backoff; data loss otherwise. Lost updates -> `UpdateAsync`.
- **Memory leaks** -> store connections, `conn:Disconnect()` on cleanup; clear per-player tables on `PlayerRemoving`; `Debris` for transient parts.
- **Parenting before configuring** -> set properties THEN `.Parent` (avoids replicating a half-built instance).
- **CharacterAdded race** -> also handle existing `player.Character`; `:WaitForChild("HumanoidRootPart")`.
- **Client `workspace.Thing` nil under streaming** -> `WaitForChild`, tags + added-signals, or Persistent streaming mode.
- **Module table "shared" between client and server** -> it isn't; each context requires its own copy. Cross-boundary = remotes only.
- **Server-side tween jitter** -> tween on client via RemoteEvent broadcast.
- **NaN smuggled through remotes** (`0/0` passes number checks) -> `if x ~= x then return end`.
