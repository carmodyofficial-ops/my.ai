# Roblox + Luau Game Dev Reference

## Luau Idioms
- `local` everything; no globals. `local Players = game:GetService("Players")`.
- Use `task.wait()`, `task.spawn()`, `task.defer()` — NEVER deprecated `wait()`/`spawn()`/`delay()`.
- Typed Luau: `local hp: number = 100`, `local function add(a: number, b: number): number`. Add `--!strict` at top.
- Method calls with `:` (`part:Destroy()`); `.` for properties/static.
- `if x then`, `if not x then`; check nil explicitly (`if inst == nil then`). `and`/`or`, no `&&`.
- Numeric `for i = 1, 10 do`; generic `for i, v in ipairs(t)`, `for k, v in pairs(t)`. `continue` allowed.

## Client–Server Security (CRITICAL)
- Server is authoritative. NEVER trust the client. FilteringEnabled is always on.
- Exploiters fire ANY remote with ANY args at any rate. Validate EVERY arg server-side: type (`typeof(x)=="number"`), range, ownership, existence, rate-limit (per-player timestamp/cooldown).
- Do ALL damage, economy, inventory, position-authority changes on the server only. Client only sends intent + renders.
```lua
buyRemote.OnServerEvent:Connect(function(plr, id)
  if typeof(id) ~= "number" then return end
  -- verify price, funds, ownership server-side
end)
```

## Services (`game:GetService`)
- `Players`: `PlayerAdded`, `player.CharacterAdded`. Handle players already present.
- `RunService`: `Heartbeat` (physics-rate, server ok), `RenderStepped` (client render only), use `dt` param—never hardcode frame time.
- `ReplicatedStorage`: shared modules/remotes/assets. `ServerScriptService`/`ServerStorage`: server-only (never replicated).
- `UserInputService`/`ContextActionService`: input (client). `TweenService`: smooth anim. `Debris:AddItem(p,5)`. `CollectionService`: tagging.

## Code Structure
- `ModuleScript` for shared/reusable logic: `return M` then `require(path)`. Cached per-context.
- `RemoteEvent`: one-way fire-and-forget (`:FireServer`/`:FireClient`/`:FireAllClients`).
- `RemoteFunction`: request->response. NEVER yield in server handler waiting on client (exploiter can hang it / error). Prefer RemoteEvent both ways.
- `BindableEvent`/`BindableFunction`: same-context (server<->server) only.

## DataStore
- `DataStoreService:GetDataStore("Players")`. Wrap every call in `pcall` + retry with exponential backoff.
- Save on `PlayerRemoving` AND `game:BindToClose(...)` (server shutdown). Never trust unsaved in-memory state.
```lua
local ok, err = pcall(function() store:SetAsync(key, data) end)
if not ok then task.wait(2) --[[retry]] end
```
- Use `UpdateAsync` for read-modify-write to avoid overwrites; budget-limit calls.

## UI
- `ScreenGui` parented to `PlayerGui` (client). `Frame`, `TextLabel`, `TextButton`, `ImageLabel`.
- Size/Position via `UDim2.new(scale, offset, ...)` — use scale for resolution independence.
- Buttons: `btn.Activated:Connect(fn)` (covers touch + click).

## Monetization (MarketplaceService)
- GamePass: `PromptGamePassPurchase(plr, id)`; gate with `UserOwnsGamePassAsync(userId, id)` (pcall it).
- DevProduct: `PromptProductPurchase`; handle `ProcessReceipt` — MUST be idempotent (track receipt key in DataStore), return `Enum.ProductPurchaseDecision.PurchaseGranted` only after granting.

## Gotchas -> Fix
- Trusting client -> validate server-side; client never authoritative.
- Yielding in RemoteFunction server handler -> don't; return fast or use RemoteEvent.
- `wait()`/`spawn()` -> `task.wait()`/`task.spawn()`.
- Un-pcall'd DataStore -> wrap + retry; data loss otherwise.
- Memory leaks -> store connections, `conn:Disconnect()` on cleanup/death; `Debris` for transient parts.
- Parenting before configuring -> set props THEN `.Parent` (avoids replication of half-built instance).
- CharacterAdded race -> also handle `player.Character` if it already exists; wait for `HumanoidRootPart`.
