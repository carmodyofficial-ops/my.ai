# iOS: Swift + SwiftUI

## Swift essentials
- Optionals: `Int?` is `.some/.none`. Unwrap with `if let x = opt`, `guard let x = opt else { return }`, `??` default, optional chaining `a?.b?.c`. `!` force-unwrap crashes on nil — only when logically guaranteed.
- `struct` = value type (copied, thread-safe by default, no inheritance); `class` = reference type (shared, ARC-managed, inheritance). Prefer `struct` for models/state; `class` for identity/shared mutable/Obj-C interop.
- `let` immutable, `var` mutable. `mutating func` needed to change `self` in a struct method. Value types copied on assignment (copy-on-write for `Array`/`Dictionary`/`String`).
- Protocols = interfaces: `protocol Named { var name: String { get } }`. Default impls via `extension Named { ... }`. Protocol-oriented: compose behavior with extensions, not deep class trees.
- Generics: `func first<T>(_ a: [T]) -> T?`; constraints `<T: Comparable>`; `some View` (opaque return), `any Protocol` (existential, boxed).
- Error handling: `enum AppError: Error`; `func load() throws -> Data`; call with `try`/`try?` (→optional)/`try!`. `do { try f() } catch let e as AppError {} catch {}`. `Result<Success, Failure>` for stored outcomes. `defer {}` runs on scope exit.
- Enums with associated values + `switch` exhaustive matching. `if case let .success(v) = result`.
- `[weak self]`/`[unowned self]` in escaping closures to break retain cycles; inside use `guard let self else { return }`.

## Swift Concurrency
- `async` funcs + `await` suspension points. Call from a `Task { await f() }` or another async context. Never block a thread waiting.
- `Task {}` inherits actor + priority; `Task.detached {}` does not. Cancel via `task.cancel()`; check `Task.isCancelled` / `try Task.checkCancellation()`. Cancellation is cooperative.
- Parallelism: `async let a = f(); async let b = g(); let (x,y) = await (a,b)`. Or `TaskGroup`: `await withTaskGroup(of: T.self) { g in g.addTask { ... } }`.
- `actor` serializes access to its mutable state — reentrant, cross-actor calls are `await`. `@MainActor` pins type/func to main thread — annotate UI-touching code. `@globalActor` for custom isolation.
- `Sendable` = safe to cross concurrency boundaries; value types with Sendable members are; classes must be `final` + immutable or `@unchecked Sendable` with manual locking.
- `AsyncSequence`/`for await x in stream`. `AsyncStream` bridges callback/delegate APIs into async.
- Strict concurrency (Swift 6): data-race errors at compile time — isolate mutable shared state to an actor or `@MainActor`.

## SwiftUI views & state
- `struct MyView: View { var body: some View { ... } }`. Views are cheap value-type descriptions rebuilt on state change; don't do work in `body`.
- State ownership:
  - `@State` — view-owned source of truth (value types); private.
  - `@Binding` — two-way reference to state owned elsewhere: `@Binding var text: String`, pass `$text`.
  - `@Observable` (macro, iOS 17+) — reference model; views auto-track only the properties they read. Replaces `ObservableObject`/`@Published`.
  - `@Environment(\.dismiss)` / `@Environment(ModelType.self)` — inject values/objects down the tree; provide with `.environment(model)`.
  - Legacy: `@StateObject` (owns an `ObservableObject`, created once) vs `@ObservedObject` (passed in, NOT owned — recreating it loses state).
- Layout: `VStack`/`HStack`/`ZStack` (+`spacing`, `alignment`), `Spacer`, `.frame(maxWidth: .infinity)`, `.padding`, `Grid`/`LazyVGrid`. Parent proposes size, child chooses, parent positions. `GeometryReader` for measured size (greedy — wrap tightly).
- Lists: `List(items) { item in Row(item) }` needs `Identifiable` or `id:`. `ForEach` inside for sections/mixed. `.swipeActions`, `.searchable`, `.refreshable { await reload() }`.
- Navigation: `NavigationStack(path: $path) { ... .navigationDestination(for: Item.self) { ItemView($0) } }`; `path` is a `NavigationPath`/typed array for programmatic push/pop/deep-link. `NavigationSplitView` for sidebar layouts. `.sheet(isPresented:)`, `.fullScreenCover`, `.alert`, `.confirmationDialog`.
- Modifiers order matters: `.padding().background()` ≠ `.background().padding()`.
- Lifecycle: `.task { await load() }` (auto-cancels on disappear), `.onAppear`/`.onDisappear`, `.onChange(of: x) { old, new in }`, `@Environment(\.scenePhase)`. App entry: `@main struct App: App { var body: some Scene { WindowGroup { ContentView() } } }`.

## Combine (still used for reactive streams)
- `Publisher` → `Subscriber`. `@Published var x` exposes `$x` publisher. `.sink { }` / `.assign(to:)`. Store `AnyCancellable` in a `Set<AnyCancellable>` or the subscription cancels immediately.
- Operators: `map`, `filter`, `debounce(for:scheduler:)` (search fields), `removeDuplicates`, `combineLatest`, `flatMap`, `catch`. `.receive(on: DispatchQueue.main)` before UI updates.
- Prefer async/await for one-shot work; Combine for continuous streams/debounced input. `.values` bridges a publisher to `AsyncSequence`.

## Data & networking
- `Codable`: `struct User: Codable`. `JSONDecoder().decode(User.self, from: data)`. `CodingKeys` enum maps JSON keys; `keyDecodingStrategy = .convertFromSnakeCase`; `dateDecodingStrategy = .iso8601`. Custom `init(from:)` for irregular JSON.
- URLSession async: `let (data, resp) = try await URLSession.shared.data(from: url)`; check `(resp as? HTTPURLResponse)?.statusCode`. Build requests with `URLRequest` (method/headers/body). Cancellation propagates through `Task`.
- Persistence: `SwiftData` (iOS 17+) — `@Model class Item {}`, `@Query var items: [Item]`, `modelContext.insert/delete`, `.modelContainer(for: Item.self)`. `Core Data` for older targets / fine-grained control. `UserDefaults` only for small prefs; `Keychain` for secrets.

## Swift language extras
- `extension Type { }` add methods/computed props/conformances (retroactively). `access control`: `open`/`public`/`internal`(default)/`fileprivate`/`private`. `final` classes/methods enable devirtualization.
- Property wrappers: `@propertyWrapper` (basis of `@State`, `@AppStorage(key)` for UserDefaults-backed). Computed vs stored props; `didSet`/`willSet` observers; `lazy var` deferred init.
- Value semantics + copy-on-write; `inout` params; trailing closures; `@escaping` (stored/async closures) vs non-escaping. `Equatable`/`Hashable`/`Comparable`/`Identifiable` conformances.
- Prefer `struct` + protocols; `enum` for finite states; avoid class inheritance unless needed (UIKit/framework interop).

## SwiftUI animation, gestures, drawing
- Animation: `withAnimation(.spring) { state = x }`; `.animation(_, value:)`; `.transition(.slide/.opacity)`; `matchedGeometryEffect` for hero transitions; `PhaseAnimator`/`KeyframeAnimator` (iOS 17+).
- Gestures: `.gesture(DragGesture().onChanged/.onEnded)`, `TapGesture`, `LongPressGesture`, `.simultaneousGesture`. `@GestureState` for transient drag state.
- Drawing: `Canvas`, `Path`, `Shape` protocol, `.clipShape`, gradients. `.accessibilityLabel`/`.accessibilityElement` — always label controls/images; test with VoiceOver.

## Testing, previews, tooling
- **Swift Testing** (iOS 18+/Xcode 16): `@Test func x() { #expect(a == b) }`, `#require`, parameterized `@Test(arguments:)`. Legacy **XCTest**: `XCTAssertEqual`, `async` tests, `XCUITest` for UI automation.
- **Previews**: `#Preview { MyView() }` — live canvas, multiple states/devices; inject sample data + environment. Fast iteration without running the app.
- Instruments (Time Profiler, Allocations, Leaks, SwiftUI view-body counts), `MetricKit` for field metrics, `os_log`/`Logger`. SPM for dependencies; `@main` app; schemes for dev/prod.

## Gotchas -> Fix
- **UI update off main thread** ("Publishing changes from background") → crash/undefined. Fix: `@MainActor` on the model/method, or `await MainActor.run {}` / `.receive(on: .main)`.
- **Retain cycle** with closures capturing `self` (timers, Combine sinks, escaping callbacks) → view/VM never deallocs. Fix: `[weak self]` + `guard let self`.
- **`@ObservedObject` for owned object** → recreated every parent render, state resets. Fix: `@StateObject` (or `@State` with `@Observable`).
- **Force-unwrap crash** on optional/`try!`/array index. Fix: `guard let`/`if let`, `?.`, bounds-check.
- **View identity churn**: `id:` or `key` changing when data shifts → animations/state break; wrong `ForEach` id (index) reuses state. Fix: stable `Identifiable` id.
- **`GeometryReader` collapses layout** (fills parent, breaks stacks). Fix: put it low in the tree, or use `.containerRelativeFrame`/`ViewThatFits`/layout `alignmentGuide`.
- **Heavy work in `body`** → recomputed every render, jank. Fix: precompute in the model, cache, `.task`.
- **`@State` not persisting across pushes**: state lives with the view instance; navigation may recreate it. Fix: lift state to a model in the environment / navigation path.
- **Blocking async on main**: `DispatchQueue.main.sync` or synchronous network → freeze/deadlock. Fix: `await` off-main work, hop to main only for UI.
- **Decoding fails silently swallowed by `try?`** → nil, no reason. Fix: `do/catch` and log the `DecodingError` (it names the key/type mismatch).
- **`Task` in `body` re-runs**: use `.task { }` modifier (tied to view lifetime) not `Task {}` in `body`.
- **Simulator vs device**: background time, push, camera, performance, memory pressure differ — profile on a real device with Instruments (Time Profiler, Allocations, Leaks).
