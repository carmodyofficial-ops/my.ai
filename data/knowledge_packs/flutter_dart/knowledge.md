# Flutter + Dart

## Dart essentials
- Null safety: `String` non-null, `String?` nullable. `?.` safe access, `??`/`??=` defaults, `!` non-null assertion (throws if null), `late` deferred non-null init. `required` named params.
- `final` (single assign, runtime) vs `const` (compile-time constant, canonicalized — reuse `const Widget()` to skip rebuilds). `var`/type inference.
- Async: `Future<T>` (single value) + `async`/`await`; `Stream<T>` (many values) + `await for`/`.listen()`. `Future.wait([...])` parallel. Errors: `try/catch/finally`, `Future.error`, stream `onError`.
- `Isolate` = separate memory + event loop for true parallelism (CPU-heavy work); no shared memory — message passing. `compute(fn, arg)` runs `fn` in a background isolate (JSON parse, image work) to avoid jank.
- Collections: `List`/`Map`/`Set`, spread `...`, collection-if/for, `map`/`where`/`fold`. Named + optional params, cascades `..`, `factory` constructors, mixins `with`, extension methods.

## Widgets
- Everything is a widget; UI = immutable widget tree rebuilt on change. `StatelessWidget` (no mutable state, `build(context)`) vs `StatefulWidget` (+ `State<T>` holding mutable fields, `setState(() { ... })` to rebuild).
- `State` lifecycle: `initState()` (once, subscribe/controllers), `didChangeDependencies()`, `didUpdateWidget()`, `build()`, `dispose()` (cancel controllers/streams/animations — mandatory to avoid leaks). `mounted` guards async setState.
- Keys: `Key`/`ValueKey`/`ObjectKey` preserve element/state identity when widgets reorder in a list; `GlobalKey` to access state/context across tree (use sparingly). Without keys, reordered stateful items mix up state.
- Composition over inheritance: build UI by nesting small widgets; extract widgets (not helper methods) so subtrees can rebuild independently and be `const`.

## Layout & constraints
- **Constraints go down, sizes go up, parent sets position.** A widget gets min/max constraints from parent, picks its size within them, parent positions it.
- `Row`/`Column` (+`mainAxisAlignment`, `crossAxisAlignment`, `mainAxisSize`), `Expanded`/`Flexible` (fill remaining), `Stack`/`Positioned`, `Container` (padding/margin/decoration), `Padding`, `Center`, `SizedBox`, `Align`. `MediaQuery.of(context).size`, `LayoutBuilder` for constraint-aware layout.
- Scrolling: `ListView.builder(itemCount, itemBuilder)` (lazy), `GridView`, `CustomScrollView`+`Sliver*` for advanced. `SingleChildScrollView` for small content.
- Material (`Scaffold`, `AppBar`, `ElevatedButton`) / Cupertino widgets; `Theme.of(context)`.

## State management
- `setState` — local, ephemeral widget state. Fine for a checkbox/animation; doesn't scale to shared/app state.
- `InheritedWidget` — propagate data down the tree efficiently (basis of `Theme`, `MediaQuery`, Provider).
- **Provider** — `ChangeNotifierProvider` + `ChangeNotifier` (`notifyListeners()`), read with `context.watch<T>()`/`context.read<T>()`/`Consumer`. Simple, common.
- **Riverpod** — compile-safe, provider outside the tree, `ref.watch`/`ref.read`, `Provider`/`StateNotifierProvider`/`NotifierProvider`/`FutureProvider`/`StreamProvider`, `AsyncValue` (`.when(data/loading/error)`). Auto-dispose, testable.
- **Bloc/Cubit** — events → states via streams; `BlocProvider`, `BlocBuilder`, `emit(state)`. Good for complex, event-driven, testable flows.
- Keep business logic out of widgets; expose immutable state; rebuild the smallest subtree.

## Navigation
- Imperative Navigator 1.0: `Navigator.push(context, MaterialPageRoute(builder: ...))`, `Navigator.pop(context, result)`, named routes (`routes:` map, `pushNamed`).
- Declarative/URL-driven: **go_router** (recommended for deep links/web) — `GoRouter(routes: [GoRoute(path, builder)])`, `context.go('/x')`/`context.push`, path params, redirects/guards, nested `ShellRoute` for bottom nav.

## Platform channels
- Call native (Kotlin/Swift) from Dart: `MethodChannel('app/battery').invokeMethod('getLevel')`; native side registers a handler. `EventChannel` for native→Dart streams (sensors). `Pigeon` generates type-safe channel code. FFI (`dart:ffi`) for C libs.

## Data, networking & persistence
- Networking: `http` package (`http.get(Uri.parse(url))`) or **Dio** (interceptors, cancel tokens, retries, form-data). Decode JSON: `jsonDecode(res.body)` → map to models; use `freezed` + `json_serializable` (`fromJson`/`toJson`, codegen via `build_runner`) for immutable typed models with `copyWith`.
- Async UI: `FutureBuilder`/`StreamBuilder` (`snapshot.hasData`/`hasError`/`connectionState`) — but store the future in state, don't create it in `build`. Prefer a state-mgmt layer (Riverpod `FutureProvider`/`AsyncNotifier` with `AsyncValue.when`) over raw builders for anything non-trivial.
- Persistence: `shared_preferences` (key-value prefs), `flutter_secure_storage` (Keychain/Keystore for tokens), **Drift**/**Isar**/`sqflite` (structured DB, reactive queries), `path_provider` for files/dirs. Offline: local DB as source of truth, sync in background.

## Animation
- Implicit: `AnimatedContainer`/`AnimatedOpacity`/`AnimatedPositioned`/`AnimatedSwitcher` animate to new values automatically over a `Duration` + `Curve`. `Hero(tag)` for shared-element route transitions.
- Explicit: `AnimationController(vsync: this, duration:)` (needs `TickerProviderStateMixin`) + `Tween(begin,end).animate(controller)`; drive with `controller.forward()`/`repeat()`; rebuild via `AnimatedBuilder`/`ListenableBuilder` or `.addListener(setState)`. Always `controller.dispose()`.
- `CurvedAnimation`, `TweenSequence`, staggered animations. For 60/120fps custom drawing use `CustomPainter`. Rive/Lottie for designer animations.

## Forms, theming, adaptive UI
- Forms: `Form(key: GlobalKey<FormState>())` + `TextFormField(validator:, onSaved:)`; `formKey.currentState!.validate()/.save()`. `TextEditingController` for controlled input (dispose it). `FocusNode` for focus.
- Theming: `MaterialApp(theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor)), darkTheme:, themeMode:)`; Material 3 (`useMaterial3: true`). Read via `Theme.of(context)`; custom tokens via `ThemeExtension`.
- Adaptive/responsive: `LayoutBuilder`/`MediaQuery` breakpoints, `Wrap`, `Flexible`; `OrientationBuilder`; Cupertino widgets or `.adaptive` constructors for iOS look. `SafeArea` for notches. `Directionality` + `EdgeInsetsDirectional` for RTL/i18n; `intl` package + `flutter_localizations`.

## Testing & tooling
- Unit/widget: `flutter_test` — `test()`, `testWidgets((tester) async { await tester.pumpWidget(); await tester.tap(find.byType(Button)); await tester.pumpAndSettle(); expect(find.text('x'), findsOneWidget); })`. `pump` advances one frame; `pumpAndSettle` runs animations to rest. `mocktail`/`mockito` for fakes. `golden` tests for pixel snapshots.
- Integration: `integration_test` package on device; `patrol`/`maestro` for E2E. Analyze with `flutter analyze` + `analysis_options.yaml` (lints). `dart format`. Hot reload preserves state; hot restart resets.
- DevTools: widget inspector, timeline (jank), memory, CPU profiler. Build modes: debug (JIT, asserts), profile (perf), release (AOT, optimized). **Impeller** is the default renderer (precompiled shaders → less first-run jank than Skia).

## Gotchas -> Fix
- **`setState` rebuilds too much** (whole large `build`) → jank. Fix: extract child widgets, push state down, `const` subtrees, use a state mgmt scope so only listeners rebuild.
- **"Unbounded/infinite constraints"** (e.g. `ListView`/`Column` inside a `Row`/unbounded parent, `Column` in `Column`) → layout exception. Fix: wrap child in `Expanded`/`Flexible`, give a `SizedBox` height, or `shrinkWrap: true` (costly).
- **"RenderFlex overflowed by N pixels"**: content wider/taller than space. Fix: `Expanded`/`Flexible`, `Wrap`, `FittedBox`, or make it scrollable.
- **BuildContext across async gap** ("don't use context after await" — widget may be unmounted). Fix: check `if (!mounted) return;` before using `context`/`setState` post-await; capture needed objects before the await.
- **Forgot `dispose()`** of controllers (`AnimationController`, `TextEditingController`, `StreamSubscription`, `ScrollController`) → memory leak / "used after dispose". Fix: dispose in `State.dispose()`.
- **Heavy work on UI isolate** (JSON parse, crypto, image decode) → dropped frames. Fix: `compute()`/`Isolate` for CPU work; keep `build` cheap and pure.
- **`ListView` without `.builder`** builds all children eagerly → slow/OOM for long lists. Fix: `ListView.builder`/`GridView.builder` (lazy) + item extent when fixed.
- **Missing/unstable keys in reorderable lists**: state attaches to wrong item after reorder/insert. Fix: `ValueKey(item.id)`.
- **Rebuilds not happening**: mutating an object in place without `notifyListeners()`/new state, or `const` widget that never rebuilds. Fix: emit new immutable state / call notify; don't `const` something that must change.
- **`MediaQuery`/`Theme.of(context)` at wrong context** (above the provider) → null/defaults. Fix: use a `Builder`/child context below the widget that supplies it.
- **Debug vs release perf**: debug (JIT) is much slower and shows shader jank. Fix: profile in **profile mode** (`flutter run --profile`), benchmark release; use DevTools timeline + `--trace-skia` / impeller for shader jank.
- **Overusing `GlobalKey`** → perf cost, brittle. Fix: pass callbacks/state down instead.
- **Async in `build`** (kicking off futures each rebuild). Fix: start in `initState`/provider; use `FutureBuilder`/`StreamBuilder` with a stored future, not one created inline in build.
- **`Expanded`/`Flexible` outside a Flex** (`Row`/`Column`/`Flex`) → assertion. Fix: only use them as direct children of a flex widget.
- **Comparing/rebuilding on mutable objects**: `freezed`/immutable models give value equality; mutable classes default to identity. Fix: use immutable models + `copyWith`, or override `==`/`hashCode`.
- **`double`/`int` type mismatch from JSON** (Dart is strict): `1` decodes as `int`, breaks `double` field. Fix: `(json['x'] as num).toDouble()`.
