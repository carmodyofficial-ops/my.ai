# Kotlin Advanced

(Assumes basics. Focus: coroutines/Flow, generics/variance, DSLs, sealed/inline/value classes, delegation, multiplatform.)

## Coroutines: structured concurrency
- A coroutine runs inside a `CoroutineScope`; children inherit its `CoroutineContext` (Job + Dispatcher + name + exception handler). Structured concurrency = a scope doesn't complete until all its children do; cancelling the scope cancels all children.
- `launch { }` → fire-and-forget, returns `Job`. `async { }` → returns `Deferred<T>`, `.await()` for the result. `runBlocking { }` bridges blocking↔suspend (tests/main only, never in prod suspend code).
- `coroutineScope { }` (suspending) awaits all children, propagates the first failure and cancels siblings. `supervisorScope { }` isolates child failures (one child failing doesn't cancel others).
- `withContext(Dispatchers.IO) { }` switches dispatcher for a block and returns its value. **Dispatchers**: `Default` (CPU, #cores threads), `IO` (blocking I/O, elastic pool), `Main` (UI, single thread), `Unconfined` (avoid).
- `suspend fun` can only be called from another suspend fn or a coroutine builder. Suspension points (`suspend` calls) are where cancellation/dispatch happen.
- Android: `viewModelScope`, `lifecycleScope`. Structured lifetime prevents leaks.

## Cancellation (cooperative)
- Cancellation is cooperative — a coroutine must check it. Suspending functions in `kotlinx.coroutines` throw `CancellationException` at suspension points. Tight CPU loops don't cancel unless you call `ensureActive()` / `yield()` / check `isActive`.
- `CancellationException` is swallowed by the machinery — **don't catch-all it**: `catch (e: Exception)` swallows cancellation and breaks structured concurrency. Rethrow it, or catch specific types, or use `catch (e: CancellationException) { throw e }`.
- Cleanup after cancellation must run in `withContext(NonCancellable) { }` (the coroutine is already cancelled, further suspends fail otherwise). Use `try/finally` or `use {}`.
- `withTimeout(ms) { }` throws `TimeoutCancellationException`; `withTimeoutOrNull` returns null.

## Flow (cold async streams)
- `flow { emit(x) }` is **cold** — nothing runs until a terminal `collect { }`; each collector re-runs the builder. Operators: `map`, `filter`, `transform`, `onEach`, `take`, `debounce`, `distinctUntilChanged`, `flatMapLatest`/`flatMapMerge`/`flatMapConcat`, `combine`, `zip`, `scan`, `retry`, `catch`.
- Terminal: `collect`, `toList`, `first`, `single`, `reduce`, `fold`, `stateIn`, `launchIn(scope)`.
- Context: the flow body must not `emit` from a different context — use `flowOn(Dispatchers.IO)` (changes *upstream* context, preserves collector context). Never wrap `emit` in `withContext`.
- Backpressure: collection suspends the emitter (built-in). `buffer()`, `conflate()` (keep latest), `collectLatest` (cancel slow processing on new value).
- **StateFlow** — hot, always has a current `.value`, conflated, emits latest to new collectors, dedups equal values. State holder: `MutableStateFlow(initial)`. **SharedFlow** — hot, configurable `replay`/`extraBufferCapacity`, for events (no initial, doesn't dedup). Convert cold→hot: `flow.stateIn(scope, SharingStarted.WhileSubscribed(5000), initial)` / `shareIn`.
- `channelFlow { send(...) }` for concurrent emission from multiple coroutines (`emit` isn't thread-safe; `send` is). `callbackFlow` bridges callback APIs + `awaitClose`.

## Exception handling in coroutines
- `launch`: exceptions propagate up to the parent scope immediately (crash unless a `CoroutineExceptionHandler` in the *root* scope handles). `async`: exception is held, thrown on `.await()`.
- `CoroutineExceptionHandler` only works at the top-level `launch` of a scope (not for `async`, not for inner coroutines). `try/catch` around a suspend call catches its exception normally.
- A child failure cancels the parent + siblings unless under `supervisorScope`/`SupervisorJob`.

## Generics & variance
- **Declaration-site variance**: `out T` (covariant, producer — `T` only in output positions, `List<out E>`), `in T` (contravariant, consumer — `T` only in input, `Comparable<in T>`). `Producer<Cat>` is a `Producer<Animal>` with `out`.
- **Use-site variance** (type projection): `Array<out Any>` (read-only view), `MutableList<in String>`. Star projection `List<*>` = unknown but safe.
- Upper bounds: `<T : Comparable<T>>`; multiple via `where T : A, T : B`.
- **`reified`** type params (only in `inline fun`): access the real type at runtime — `inline fun <reified T> parse(s: String): T` enables `T::class`, `is T`, `as T`. Without `inline`+`reified`, generic types are erased.

## sealed / enum / inline / value classes
- `sealed class`/`sealed interface` — closed hierarchy known at compile time; exhaustive `when` (no `else` needed, compiler enforces). Permitted subtypes must be in the same module/package. Model states/results: `sealed interface Result { data class Ok(val v: T); data class Err(val e: Throwable) }`.
- `data class` — auto `equals`/`hashCode`/`toString`/`copy`/`componentN` (destructuring). Only primary-constructor `val`/`var` count toward equals.
- **`value class`** (`@JvmInline value class UserId(val raw: String)`) — zero-cost wrapper, inlined to the underlying type at runtime, type-safety without allocation. One property only. Boxes when used as a nullable/generic/interface type.
- **`inline fun`** — body copied to call site, eliminates lambda allocation; enables `reified`, non-local `return` from lambdas, `crossinline` (forbid non-local return), `noinline` (keep a lambda as an object). Overuse bloats bytecode; reserve for higher-order fns.

## Delegation (`by`)
- **Class delegation**: `class MyList(b: List<T>) : List<T> by b` — forwards interface methods to `b`, override selectively. Composition over inheritance.
- **Property delegation**: `val x by lazy { compute() }` (thread-safe once), `var y by Delegates.observable(init) { _, old, new -> }`, `var z by Delegates.vetoable(...)`, `val v by map` (map-backed), custom via `operator fun getValue`/`setValue`. `by viewModels()`, `by remember {}` (Compose) are delegates.

## DSL building (lambda with receiver)
- Function type with receiver `A.() -> Unit` — inside the lambda, `this` is the receiver, its members are in scope. That's how `apply`, `buildString`, HTML/Gradle-Kotlin DSLs read declaratively.
```kotlin
fun table(init: Table.() -> Unit): Table = Table().apply(init)
table { row { cell("a") } }   // this == Table, then Row, then...
```
- `@DslMarker` annotation prevents implicit access to outer receivers (scope control) — avoids calling outer-scope members by accident in nested builders.
- Scope functions: `apply`/`also` return the receiver (`apply` uses `this`, `also` uses `it`); `let`/`run`/`with` return the lambda result (`run`/`with` use `this`, `let` uses `it`). `?.let { }` for nullable transforms.

## Extension functions & contracts
- Extensions are resolved **statically** on the declared (compile-time) type, not the runtime type — no true polymorphism, no access to private members. `fun String.shout() = uppercase()`.
- Extension on nullable receiver: `fun String?.orEmpty()`. Member wins over extension if both exist (same signature).
- `contract { }` (experimental-ish, stable in stdlib) informs the compiler about smart-casts / invocation: `returns() implies (x != null)`, `callsInPlace(block, EXACTLY_ONCE)` — enables smart-cast after your validating function and `val` init in lambdas.

## Kotlin Multiplatform (KMP)
- Share code across JVM/Android/iOS/JS/Native/Wasm. `commonMain` holds shared code; platform source sets (`androidMain`, `iosMain`) provide `actual` implementations for `expect` declarations. `expect fun platformName(): String` / `actual fun`.
- Common libs: coroutines, kotlinx-serialization, Ktor (networking), SQLDelight, Compose Multiplatform. iOS interop via Kotlin/Native → Obj-C/Swift framework. Business logic shared; UI often per-platform (or Compose MP).

## Gotchas -> Fix
- **Catching `CancellationException`**: `try { } catch (e: Exception) { }` swallows cancellation, breaks structured concurrency -> rethrow `CancellationException` or catch specific exceptions.
- `GlobalScope.launch` = unstructured, leaks, no lifecycle -> use a proper scope (`viewModelScope`, `coroutineScope { }`).
- Blocking call (`Thread.sleep`, JDBC, sync I/O) inside a coroutine on `Default`/`Main` starves the pool/freezes UI -> wrap in `withContext(Dispatchers.IO)` or use suspend APIs.
- `async` without `await` swallows its exception; two `async` then sequential `await` still runs concurrently (they start eagerly) — but launching then awaiting one-at-a-time in a loop serializes -> collect Deferreds first, `awaitAll`.
- Cold Flow re-executes per collector (duplicate network calls) -> `shareIn`/`stateIn` to make hot/shared.
- `emit` from wrong context throws "Flow invariant violated" -> use `flowOn` upstream, never `withContext { emit() }`; use `channelFlow` for concurrent emission.
- StateFlow drops values equal to current (`equals` dedup) and conflates fast updates — consumers may miss intermediate states; use SharedFlow (or `distinctUntilChanged`-free channel) for events.
- Reified needs `inline` — plain generics are erased; `T::class` won't compile without `inline`+`reified`.
- Extension functions dispatch statically -> a `List` extension called on a variable typed `List` uses List's version even if runtime is ArrayList; don't expect override behavior.
- `value class` boxes silently when used as generic/nullable/interface — the zero-cost benefit is lost in those positions.
- `lazy` default mode is `SYNCHRONIZED` (locks) — use `LazyThreadSafetyMode.NONE` when single-threaded to avoid overhead.
- Non-exhaustive `when` on a sealed type only errors when used as an expression (assigned/returned); as a statement it may compile silently pre-1.7 -> assign/return it or annotate to force exhaustiveness.
- `runBlocking` in production suspend code blocks the thread and defeats coroutines -> only in `main`/tests.
