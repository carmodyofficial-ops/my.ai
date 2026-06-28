---
name: roblox-game-dev
description: "How to build Roblox games in Luau: server-authoritative architecture, where scripts go (ServerScriptService / StarterPlayer / ReplicatedStorage), RemoteEvents for client-server actions, DataStore persistence, leaderstats, and the common Luau/Roblox pitfalls."
version: 1.0.0
category: Coding
tags: [roblox, luau, lua, game, gamedev, datastore, remoteevent, studio, script, localscript, modulescript, leaderstats, humanoid, part, server, client, gui, tool]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when writing or structuring Roblox game code (Luau) — game systems, client↔server communication, data persistence, GUIs, tools/weapons, spawning, or scoring.

## Procedure

1. Decide where each piece runs and place it correctly. Server logic (rules, currency, validation, data) → a `Script` in **ServerScriptService**. Per-player UI/input/camera → a `LocalScript` in **StarterPlayer > StarterPlayerScripts** or **StarterGui**. Shared code/constants → a `ModuleScript` in **ReplicatedStorage** (`require` it). RemoteEvents/Functions and shared assets → **ReplicatedStorage**.
2. Make the server authoritative. The client may only request; the server validates and decides. For a client action (buy, attack, claim), create a **RemoteEvent** in ReplicatedStorage: client `:FireServer(args)`, server `OnServerEvent:Connect(function(player, args) ...validate args... end)`. Compute money/score/inventory on the server only. Use RemoteEvent (not RemoteFunction) for client→server.
3. Build instances correctly: `Instance.new("Part")`, set its properties (Size/Position/Anchored/Color), then set `.Parent = workspace` LAST. Use `:WaitForChild("X")` for anything that may not have loaded; `:FindFirstChild` when absence is OK.
4. Use the right services/APIs: `game:GetService("Players"|"ReplicatedStorage"|"RunService"|"DataStoreService"|"TweenService"|"UserInputService")`. Game loop → `RunService.Heartbeat:Connect(function(dt) end)`. Yielding → `task.wait()` (never `wait()`).
5. Persist data with DataStore on the SERVER, wrapped in `pcall`: load on `PlayerAdded`, save on `PlayerRemoving`, and add `game:BindToClose(...)` so data survives shutdown. Use `:UpdateAsync` for read-modify-write; respect rate limits.
6. Show progress with `leaderstats` (a Folder named exactly `leaderstats` under the player holding IntValue/StringValue children).
7. Verify in Studio: Play-test, watch the Output window for errors, and confirm the behavior on both a server and a client view (Test > Clients & Servers).

## Pitfalls

- Trusting the client. Client changes to Workspace don't replicate to the server (FilteringEnabled). Do authoritative work server-side.
- Deprecated `wait()`/`spawn()`/`delay()` — use `task.wait()`/`task.spawn()`/`task.delay()`.
- Not `pcall`-wrapping DataStore/HttpService — they yield and can throttle/error; unhandled errors lose data.
- Setting `.Parent` before properties (a frame of half-built state); forgetting `Anchored=true` so a Part falls.
- `Touched` fires constantly and for any part — debounce and check `FindFirstChildOfClass("Humanoid")`.
- Putting server logic in StarterGui/StarterPlayer (those copy per player) instead of ServerScriptService.
- RemoteFunction for client→server (a malicious client can yield/hang it) — use RemoteEvent.

## Verification

- Server logic is in ServerScriptService; client logic in StarterPlayer/StarterGui; shared in ReplicatedStorage.
- Every client→server action validates its inputs on the server; no currency/score is trusted from the client.
- DataStore calls are server-side, pcall-wrapped, and saved on PlayerRemoving + BindToClose.
- Play-tested in Studio with no errors in Output, on both server and client.
