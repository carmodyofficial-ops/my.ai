# Roblox Systems Architecture (Expert)

## Large-game structure (client/server/shared)
- Three roots, strict boundary: **Server** (`ServerScriptService`/`ServerStorage`, authoritative, never replicates), **Client** (`StarterPlayerScripts`/`StarterCharacterScripts`, per-player, untrusted), **Shared** (`ReplicatedStorage`, replicated + readable by exploiters). Type defs + pure logic in shared; secrets + authority server-only.
- Rojo maps folders → services (`default.project.json`). Typical: `src/server`, `src/client`, `src/shared`, `Packages` (Wally) → `ReplicatedStorage.Packages`. One bootstrapper per side; everything else is a required module, no loose Scripts scattered in the tree.
- Single bootstrapper pattern: one server `Script` and one client `LocalScript` that require an ordered list of feature modules, call `:Init()` on all, then `:Start()` on all (two-phase: Init wires refs without depending on others being started; Start assumes all Inits done). Avoids ordering races + circular startup.

## Service/controller frameworks at scale
- **Knit** — Services (server, authoritative, auto-exposed `.Client` remotes) + Controllers (client). Auto networking, lifecycle (`KnitInit`→`KnitStart`). Simple, battle-tested; weaker typing, runtime string lookups.
- **Flamework** (roblox-ts) — decorator DI (`@Service`/`@Controller`/`@Component`), compile-time dependency resolution, real interfaces/generics from TypeScript, lifecycle events (`OnStart`/`OnInit`/`OnTick`/`OnPhysics`/`OnRender`). Best type safety + testability; requires the roblox-ts toolchain.
- **Custom bootstrapper** — a plain two-phase loader (above) + a small service locator table. Zero framework magic, full control, easy to reason about; you build DI/networking yourself. Good when you want no dependency.
- Pick: Knit for fast Luau-native teams; Flamework/roblox-ts for large typed codebases + TS ecosystem; custom when the game is bespoke and you want minimal abstraction. Don't mix two DI frameworks.

## ECS with Matter (data-oriented)
- **Matter** — sparse-set ECS for Luau. **Components** = pure data (`Component()` factories, immutable — you replace, not mutate). **Entities** = ids. **Systems** = functions run each frame over `world:query(...)`. **World** holds entities+components.
```lua
local Matter = require(Packages.Matter)
local Position = Matter.component("Position")
local Velocity = Matter.component("Velocity")

local function moveSystem(world)
    for id, pos, vel in world:query(Position, Velocity) do
        world:insert(id, pos:patch({ x = pos.x + vel.x })) -- replace, immutable
    end
end
```
- Queries: `world:query(A, B):without(C)`; `world:get(id, Comp)`; `world:spawn(A(...), B(...))`; `world:despawn(id)`. Systems are ordered/scheduled by a `Loop` (`Loop.new(world, state):begin({event=RunService.Heartbeat})`).
- **Matter debugger** (`Matter.Debugger`) — inspect entities/components/queries live; huge for data-oriented debugging.
- **When ECS vs OOP**: ECS wins for many similar entities with varied behavior combinations (bullets, mobs, tiles, thousands of interacting things), hot-reloadable systems, and data-oriented cache-friendly iteration. OOP (metatable classes) wins for a few complex stateful singletons (a Shop, a MatchManager, a Quest) where inheritance/encapsulation reads clearer. Real games mix: ECS for the simulation, service objects for managers.
- Data-oriented mindset: separate data (components/plain tables) from behavior (systems/functions); iterate arrays of like data (cache-friendly) over calling virtual methods on scattered objects; prefer struct-of-arrays for hot loops.

## Single source of state + replicating it
- Server owns the authoritative state (one place — a store/replica). Never let two systems own the same fact. Client holds a read-only mirror updated by replication.
- Replicate diffs, not polls: server mutates state → emits `{path, newValue}` (or a full snapshot on join, deltas after) over one RemoteEvent. Libraries: `Replica`/`ReplicaService`, `Rocs`, roll-your-own reducer. Client applies diffs to its mirror, fires change signals for UI.
- Reducer/immutable-update pattern (Redux-like) keeps state changes traceable + testable; pairs well with feature flags + time-travel debugging.

## Module organization & dependency management (Wally)
- One responsibility per ModuleScript; name by role (`PlayerDataService`, `CombatSystem`, `types`). Group by feature, not by kind, in large codebases (`features/combat/{server,client,shared}`).
- **Wally** — `wally.toml` (deps with exact SemVer), `wally.lock` committed, `wally install` populates `Packages/` (git-ignored), synced by Rojo. `Rokit`/`Aftman` pins toolchain (rojo/wally/selene/stylua versions) in `rokit.toml` so CI + every dev match.
- Dependency hygiene: no circular `require` — extract shared types/constants to a leaf module; lazy-require inside a function to break a cycle only as a last resort. Depend on abstractions (a service interface) not concrete deep paths where possible.
- Never `require` across the client/server boundary — shared code only via `ReplicatedStorage`; server-only modules stay in `ServerStorage`/`ServerScriptService`.

## Feature flags
- Data-driven on/off + rollout: a server-authoritative flags table (from a config module, DataStore, or `MessagingService`-pushed remote config). Gate risky features (`if Flags.NewCombat then ...`), enable per-player cohorts (A/B), kill-switch a broken system live without a republish.
- Push updates cross-server with `MessagingService:PublishAsync`/`SubscribeAsync` (flag change → all servers react). Cache locally; default-off on read failure.

## Testing
- **TestEZ** — BDD (`describe`/`it`/`expect`) for Luau. **Jest-Lua** (`@rbxts/jest`/jest-lua) — Jest-style, mocks, snapshots, better for TS/Flamework stacks. Pure-logic modules (no instance deps) are trivially unit-testable — architect for that (inject services, keep logic pure).
- Run headless in CI: `run-in-roblox` (drives a real Studio) or **Open Cloud Luau execution API** (execute a task in a real server, capture results) — the modern CI path. Lune (standalone Luau runtime) for pure-Luau logic tests without Roblox APIs.
- Design for testability: separate pure logic (deterministic, injectable deps) from Roblox-API side effects; mock remotes/DataStore behind interfaces.

## CI with Rojo
- Pipeline: checkout → `rokit install` (pinned tools) → `wally install` → `selene` lint + `stylua --check` → build place with `rojo build default.project.json -o game.rbxlx` → run tests (Open Cloud Luau / run-in-roblox) → deploy via **Open Cloud** (`Publish`/`Versions` API) to a staging place, promote to prod. Everything reproducible from git.
- Keep the built place out of git; source-of-truth is the filesystem tree Rojo builds.

## Save-data schema versioning & migration
- Store a `schemaVersion` (int) in every saved profile. On load, run ordered migrations `v1→v2→v3…` until current before the game touches the data. ProfileService `:Reconcile()` fills *new* fields from a template, but **can't rename/restructure/transform** — write explicit migration functions for those.
```lua
local MIGRATIONS = {
    [1] = function(d) d.coins = d.gold; d.gold = nil end,       -- rename
    [2] = function(d) d.inventory = arrayToDict(d.inventory) end, -- reshape
}
local function migrate(data)
    data.schemaVersion = data.schemaVersion or 1
    while MIGRATIONS[data.schemaVersion] do
        MIGRATIONS[data.schemaVersion](data)
        data.schemaVersion += 1
    end
    return data
end
```
- Always additive/back-compat where possible; never delete a field a still-live older server writes. Test migrations on copies. Keep a template (default profile) for `Reconcile`. Version bumps are one-way — plan rollbacks (keep old-schema readers, or versioned DataStore backups / DataStore2).

## Scaling to many concurrent systems
- Loop/scheduler owns tick order (Matter `Loop`, Flamework `OnTick`) — deterministic system ordering beats N independent `Heartbeat:Connect`s racing.
- Budget per-frame work: stagger heavy systems across frames (round-robin entities), offload compute to Actors (parallel Luau), event-drive instead of poll. One scheduler > many uncoordinated connections.
- Cross-server coordination: `MessagingService` (pub/sub, rate-limited), `MemoryStoreService` (fast ephemeral shared state — matchmaking queues, global counters, sorted maps with TTL), `DataStore` for durable. Don't use DataStore as a message bus.

## Architectural anti-patterns
- **`_G` / `shared` globals for state** → untraceable coupling, race conditions. Fix: module returns + explicit deps / service locator.
- **God module** doing data + UI + networking + combat. Fix: split by responsibility; compose.
- **Business logic in client** that awards value. Fix: client sends intent; server decides; shared holds only pure/formula code.
- **Deep instance-tree "database"** (Folders of Value objects as state). Fix: one authoritative state table + attributes; replicate diffs.
- **Circular requires**. Fix: leaf types module; two-phase Init/Start; lazy require last resort.
- **No schema version** on saves → migration hell / data loss on a field rename. Fix: `schemaVersion` + migration chain from day one.
- **Framework soup** (Knit + Flamework + custom DI mixed). Fix: one framework; commit.

## Gotchas -> Fix
- **New save field is `nil` for existing players**: no reconcile/migration. Fix: `:Reconcile()` against a template for additive fields; explicit migration for renames/reshapes; `schemaVersion` gate.
- **Startup race: system B uses A before A initialized**: independent Scripts, undefined order. Fix: single bootstrapper, two-phase Init-all-then-Start-all.
- **Matter: mutated a component in place, other systems see stale/torn state**: components are immutable. Fix: `component:patch{...}` / `world:insert` to replace; never mutate the table.
- **ECS everywhere, even a lone MatchManager**: over-engineered, awkward. Fix: ECS for many-similar-entities simulation; plain service object for singletons.
- **Circular require deadlock/`nil` module**: A↔B at load. Fix: extract shared leaf module; lazy `require` inside a function; two-phase init.
- **Feature flag read fails → feature toggles unpredictably**: no default. Fix: default-off (or last-known) on read error; cache; push changes via MessagingService.
- **CI can't test because logic is tangled with instances**: no seams. Fix: pure logic modules + injected service interfaces; test those; mock remotes/DataStore.
- **`Reconcile` "handles migrations"** assumption: it only fills missing fields, can't transform. Fix: explicit ordered migration functions for structural changes.
- **State owned in two places** (server var + a Value object + client cache all writable): drift/dupe. Fix: one authoritative owner (server), everything else a read-only mirror updated by replication.
- **Wally deps drift between devs/CI**: unpinned tools / uncommitted lockfile. Fix: commit `wally.lock`; pin toolchain in `rokit.toml`; CI runs `rokit install` + `wally install`.
- **MessagingService/MemoryStore as durable store**: rate limits, TTL, data loss. Fix: MessagingService = ephemeral pub/sub, MemoryStore = fast ephemeral w/ TTL, DataStore = durable; use each for its job.
- **Requiring server modules from client** (or vice versa): boundary break / exploit. Fix: shared code in `ReplicatedStorage`; server-only stays server-only.
