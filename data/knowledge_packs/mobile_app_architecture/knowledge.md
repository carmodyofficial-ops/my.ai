# Mobile App Architecture

## Core principles
- **Separation of concerns** in layers: UI (screens/widgets) → presentation/state (ViewModel/Bloc/store) → domain (use cases, entities, pure business rules) → data (repositories, remote/local sources). Dependencies point inward; domain knows nothing about UI or frameworks.
- **Unidirectional data flow (UDF)**: state flows down, events flow up. Single source of truth per screen. Immutable state objects; render is a pure function of state. Maps to Compose/SwiftUI/Flutter/RN naturally.
- **Repository pattern**: presentation depends on a repository interface, not on network/DB. Repository reconciles remote + local, exposes observable state (Flow/Publisher/Stream). Enables offline, caching, testing via fakes.
- Keep platform/framework code at the edges; keep domain plain (plain Swift/Kotlin/Dart, no SDK imports) so it's testable and portable.

## Layered / clean architecture
- **Presentation**: state holders (SwiftUI `@Observable`/Android ViewModel+StateFlow/Bloc/Zustand). Hold UI state, handle events, call use cases. No business logic beyond orchestration; no direct network/DB.
- **Domain** (optional but valuable for complex apps): entities + use cases/interactors (`GetUserProfile`). Pure, synchronous-ish, no framework deps. Skip for simple CRUD apps (over-engineering).
- **Data**: repository impls, DTOs + mappers (DTO ≠ domain entity — map at the boundary), remote data source (API client), local data source (DB/cache). Handle errors/mapping here.
- MV* choices: MVVM (most common on iOS/Android), MVI (explicit intents/immutable state, good with Compose/Bloc), Redux/TCA-style unidirectional stores.

## State management patterns
- Distinguish **UI/ephemeral state** (scroll pos, toggles — keep local) from **screen state** (in a state holder) from **app/shared state** (auth/session/settings — scoped singleton).
- Model async as an explicit state: `Loading | Success(data) | Error(e) | Empty` (sealed class / enum / `AsyncValue`) — never boolean soup. Render all states.
- Scope state to lifecycle: survive config changes/process death (ViewModel + SavedState, `rememberSaveable`, restoration). Don't leak; cancel work when the owner dies.
- Prefer immutable state + copy-on-write updates; derive computed values, don't store duplicates.

## Navigation patterns
- **Type-safe, declarative routing**: Nav-Compose type-safe routes / SwiftUI `NavigationStack` path / go_router / Expo Router / React Navigation. Central route definitions.
- Decouple navigation from screens: emit a navigation event/effect from the state holder; a coordinator/router performs it — screens stay testable and reusable. (Coordinator pattern / navigator injection.)
- Support **deep links** and back-stack restoration from the start; pass IDs (not whole objects) as route params; fetch by ID at the destination.
- Nested navigation for tabbed apps (each tab its own stack); handle Android hardware back and iOS swipe-back.

## Offline-first, sync & local storage
- Treat the **local DB as source of truth**; UI observes it; network updates the DB. App works offline; network is an optimization.
- Storage tiers: key-value (UserDefaults/DataStore/MMKV/AsyncStorage) for prefs; structured DB (SwiftData/Core Data, Room, Drift/Isar, WatermelonDB/SQLite) for entities; secure store (Keychain/Keystore) for tokens; files for blobs/images.
- **Sync**: outbox/queue of pending mutations, retry with backoff, reconcile on reconnect. Conflict resolution: last-write-wins (timestamps/versions) or CRDTs for collaborative. Track per-record sync state (`pending/synced/failed`). Idempotent server ops + client-generated IDs.
- Cache invalidation: TTL/ETag/versioning; stale-while-revalidate (show cached, refresh in background).

## Networking & caching
- One HTTP client layer (URLSession/Retrofit+OkHttp/Dio/fetch+TanStack Query). Typed models, central error mapping, auth interceptor (attach token, refresh on 401 once, then logout).
- Timeouts, retries with exponential backoff + jitter (idempotent only), cancellation on screen exit. HTTP caching (ETag/Cache-Control) + app-level cache. Paginate lists (cursor > offset).
- Handle flaky mobile networks: detect connectivity, queue, don't block UI, show cached data.

## DI, modularization, testing
- **DI**: constructor injection; container/graph (Hilt, Koin, swinject/factory, Riverpod, manual). Inject interfaces → swap fakes in tests, choose impls per flavor. Scope lifetimes (singleton/screen/session).
- **Modularization**: split by feature (`:feature:login`) + shared core (`:core:network`, `:core:ui`, `:core:data`) once the app is large — faster builds, enforced boundaries, parallel teams. `internal`/visibility to hide impls. Don't over-modularize small apps.
- **Testing strategy** (pyramid): many unit tests (domain/use cases/state holders with fake repos — fast, no UI), fewer integration (repository + DB/API with test doubles), few E2E/UI (XCUITest, Espresso/Compose test, `flutter integration_test`, Maestro/Detox) on critical flows. Test state holders by asserting emitted state given events. Snapshot tests for UI regressions.

## Performance: startup, memory, battery
- **Startup**: minimize main-thread work before first frame; lazy-init heavy deps; defer non-critical work (analytics, prefetch) off the critical path. Measure cold vs warm start (Android baseline profiles / macrobenchmark; iOS Instruments App Launch). Target cold start < ~2s.
- **Rendering**: keep the main/UI thread free; 60/120fps budget (~8–16ms/frame). Virtualize long lists; avoid overdraw and deep layouts; move CPU work off-thread (isolate/coroutine/actor). Profile with the platform tools before optimizing.
- **Memory**: avoid leaks (retain cycles, undisposed controllers, context leaks); downsample images to display size; cache with bounds (LRU). Watch bitmap/image memory.
- **Battery/network**: batch/coalesce network + wakeups; respect background execution limits (Android Doze/WorkManager, iOS BGTaskScheduler); use push instead of polling; throttle location/sensors.

## Native vs cross-platform decision
- **Native (Swift/SwiftUI + Kotlin/Compose)**: best perf, platform fidelity, immediate access to new OS APIs; 2 codebases, 2 skill sets. Choose for heavy platform integration, graphics/AR, or when UX polish per-OS is paramount.
- **Flutter**: single codebase, own rendering engine (consistent UI, high perf), great for custom/branded UI; larger binary, Dart, platform-look requires effort.
- **React Native**: single JS/TS codebase, reuse web skills/ecosystem, near-native lists/animations with Reanimated + New Arch; native modules for gaps. Good when team is JS-heavy or sharing logic with web.
- **KMP (Kotlin Multiplatform)**: share business/domain/data logic, native UI per platform — a middle path. **Compose Multiplatform** extends UI sharing.
- Decide on: team skills, UI complexity/fidelity, performance needs, platform-API depth, time-to-market, long-term maintenance, hiring.

## Gotchas -> Fix
- **Business logic in UI/widgets** → untestable, duplicated. Fix: push to use cases/state holders; keep views dumb.
- **God ViewModel / massive view controller**: one class doing everything. Fix: split by responsibility, extract use cases, feature modules.
- **DTOs leaking into UI**: API shape drives the whole app; breaks on backend change. Fix: map DTO→domain at the data boundary.
- **No offline handling**: blank screens on flaky networks. Fix: local-source-of-truth, cache, explicit Loading/Error/Empty states.
- **Passing whole objects through navigation** → serialization/staleness bugs. Fix: pass IDs, refetch at destination.
- **Singletons everywhere / hidden global state** → order-dependent bugs, hard tests. Fix: DI with scoped lifetimes, inject interfaces.
- **Blocking the main thread** (sync IO/JSON/crypto) → jank/ANR. Fix: offload (coroutine/isolate/actor/worker); keep UI thread for UI.
- **Ignoring config changes / process death** → lost state on rotate/low-memory kill. Fix: hoist to ViewModel/saved state, restoration APIs.
- **Premature modularization/clean-arch on a tiny app** → boilerplate tax. Fix: match architecture to complexity; add layers as it grows.
- **Optimizing without measuring**: guess-based perf work. Fix: profile first (frame/startup/memory tools), fix the actual bottleneck.
