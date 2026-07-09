# Android: Kotlin + Jetpack Compose

## Kotlin for Android
- Null safety: `String` non-null, `String?` nullable. `?.` safe call, `?:` Elvis default, `!!` throws (avoid), `?.let { }` run-if-non-null. Prefer `val` (immutable) over `var`.
- `data class User(val id: String, val name: String)` → auto `equals`/`hashCode`/`copy`/`componentN`/`toString`. `copy(name = "x")` for immutable updates.
- `sealed class`/`sealed interface` → exhaustive `when` (no `else` needed) for state/results: `sealed interface UiState { object Loading; data class Success(val d: T); data class Error(val e: Throwable) }`.
- Coroutines: `suspend fun` for async; launch in a `CoroutineScope` (`viewModelScope`, `lifecycleScope`). `launch {}` fire-and-forget, `async {}`/`await()` for a result, `coroutineScope {}`/`supervisorScope {}` structured. `withContext(Dispatchers.IO)` for blocking IO, `Dispatchers.Default` CPU, `Main` UI. Structured concurrency: cancelling parent cancels children.
- Flow: cold async stream. `flow {}`, `map`/`filter`/`combine`/`debounce`. `StateFlow` (hot, holds current value, for UI state) / `SharedFlow` (events). Collect with `.collectAsStateWithLifecycle()` in Compose (stops in background). `stateIn(scope, SharingStarted.WhileSubscribed(5000), initial)`.
- Scope funcs: `let`/`run`/`with`/`apply`(returns receiver, config)/`also`(side effect). Extension funcs, higher-order funcs, trailing lambdas.

## Jetpack Compose
- Composable = `@Composable fun Greeting(name: String) { Text("Hi $name") }`. UI is a function of state; Compose re-invokes (recomposes) on state change. Declarative, no XML.
- State: `var count by remember { mutableStateOf(0) }`. `remember` survives recomposition; `rememberSaveable` survives config change/process death (must be Bundle-able). Reading a `State` subscribes that scope to changes.
- State hoisting: make composables stateless — pass `value` + `onValueChange` up to the caller/ViewModel. Single source of truth, reusable, testable.
- Recomposition: only scopes reading changed state re-run; skippable if params are `@Stable`/`@Immutable` and unchanged. Compose may recompose out of order / in parallel / frequently — composables must be side-effect-free and idempotent.
- Side effects:
  - `LaunchedEffect(key)` — run suspend work tied to composition; restarts when `key` changes; cancels on leave. Use for one-shot loads/animations.
  - `rememberCoroutineScope()` — launch coroutines from callbacks (button click).
  - `DisposableEffect(key)` — register + `onDispose { }` cleanup (listeners, sensors).
  - `derivedStateOf {}` — computed state that only re-emits when result changes (avoid recompute storms).
  - `rememberUpdatedState` — capture latest value in a long-lived effect. `SideEffect {}` — publish state to non-Compose.
- Layout: `Column`/`Row`/`Box` (+`Modifier`, `Arrangement`, `Alignment`). `Modifier` order matters (`.padding().background()` ≠ reverse). `Modifier.weight`, `.fillMaxWidth`, `ConstraintLayout` for complex. Material3: `Scaffold`, `TopAppBar`, `Button`, `Card`, `Theme`.
- Lists: `LazyColumn`/`LazyRow` — only compose visible items. `items(list, key = { it.id })` — stable keys prevent state loss/animation glitches. Avoid nesting scrollables of the same axis.
- Navigation: Navigation-Compose. `NavHost(navController, startDestination) { composable("home") { } ; composable("detail/{id}") { backStack -> backStack.arguments?.getString("id") } }`. `navController.navigate("detail/$id")`, `popBackStack()`. Type-safe routes (2.8+) with `@Serializable` route objects.

## ViewModel + lifecycle
- `class MyViewModel : ViewModel()` — survives config changes, holds UI state as `StateFlow`, launches work in `viewModelScope` (auto-cancelled in `onCleared`). Never hold `Context`/`View`/Activity refs (leak) — use `AndroidViewModel`/`Application` if needed.
- Get in Compose: `val vm: MyViewModel = viewModel()` or Hilt `hiltViewModel()`. Expose immutable `StateFlow`, collect with `collectAsStateWithLifecycle()`.
- Lifecycle: prefer lifecycle-aware collection; `repeatOnLifecycle(STARTED)` for flows in Activities/Fragments. Unidirectional data flow: events up → ViewModel → state down.

## Data layer
- Room: `@Entity`, `@Dao` with `@Query`/`@Insert(onConflict=REPLACE)`/`@Update`; return `Flow<List<T>>` for reactive reads. `@Database(entities=[...], version=n)`; provide `Migration` on schema change (or `fallbackToDestructiveMigration` in dev only).
- Retrofit: `interface Api { @GET("users/{id}") suspend fun user(@Path("id") id: String): User }`. `Retrofit.Builder().baseUrl().addConverterFactory(kotlinx-serialization/Moshi)`. Wrap calls in `try/catch` (IOException, HttpException); do IO on `Dispatchers.IO` (Retrofit suspend funcs already switch).
- Repository pattern: single source of truth, expose Flow, cache in Room, fetch from Retrofit, reconcile.

## Hilt DI
- `@HiltAndroidApp` on `Application`; `@AndroidEntryPoint` on Activity/Fragment. `@HiltViewModel class VM @Inject constructor(repo: Repo)`. `@Module @InstallIn(SingletonComponent::class)` with `@Provides`/`@Binds`. Scopes: `@Singleton`, `@ViewModelScoped`. `@Inject constructor` for your own classes.

## Compose animation, theming, permissions, background
- Animation: `animate*AsState` (`animateFloatAsState`, `animateColorAsState`) for single values; `AnimatedVisibility`, `AnimatedContent`, `Crossfade`; `updateTransition` for coordinated; `rememberInfiniteTransition`. `Modifier.animateContentSize()`, `animateItem()` in LazyColumn.
- Theming: Material3 `MaterialTheme(colorScheme, typography, shapes)`; `dynamicColor` (Material You, from wallpaper, API 31+); `isSystemInDarkTheme()` for dark mode. Access via `MaterialTheme.colorScheme`.
- Permissions: declare in `AndroidManifest.xml`; request runtime perms with `rememberLauncherForActivityResult(RequestPermission())` or Accompanist Permissions; handle denied/"don't ask again" (send to app settings). Scoped storage / photo picker for media.
- Background work: **WorkManager** for deferrable guaranteed work (`OneTimeWorkRequest`/`PeriodicWorkRequest`, constraints, backoff); foreground service (with declared type) for ongoing; respect Doze/battery limits. Notifications via `NotificationCompat` + channels (API 26+) + POST_NOTIFICATIONS runtime perm (API 33+).

## Testing & tooling
- Unit: JUnit + coroutines `runTest` + Turbine (Flow) + MockK. Test ViewModels: emit events, assert `StateFlow` values.
- UI: Compose test — `composeTestRule.setContent {}`, `onNodeWithText("x").assertIsDisplayed().performClick()`, semantics-based. Espresso for View-based. E2E on device/emulator; screenshot tests (Paparazzi/Roborazzi).
- Build: Gradle + Kotlin DSL, `libs.versions.toml` version catalog, KSP (not kapt) for annotation processors. R8 shrink/obfuscate in release. `./gradlew test connectedAndroidTest lint`. Baseline profiles + macrobenchmark for startup/jank.

## Gotchas -> Fix
- **Recomposition storm**: reading frequently-changing state high in the tree, or lambdas/objects allocated in composition. Fix: hoist state low, `derivedStateOf`, stable/immutable params, `remember` heavy calcs, pass method refs.
- **Lost `LazyColumn` item state / bad scroll on update** → missing/unstable `key`. Fix: `items(list, key = { it.id })`.
- **`remember` without keys holds stale data** when input changes. Fix: `remember(inputKey) { }` or `LaunchedEffect(inputKey)`.
- **Effect restarts every recomposition** because an unstable `key` (new lambda/object) is passed. Fix: stable key, `rememberUpdatedState` for latest value, `Unit`/id key for one-shot.
- **Blocking the main thread** (network/DB/`runBlocking` on Main) → ANR. Fix: `suspend` + `withContext(Dispatchers.IO)`, never `runBlocking` on UI.
- **Context/View leak in ViewModel or long coroutine** outliving the screen. Fix: no UI refs in ViewModel; `viewModelScope`; cancel jobs.
- **Collecting Flow without lifecycle** keeps working in background, wastes battery/crashes. Fix: `collectAsStateWithLifecycle()` / `repeatOnLifecycle`.
- **Config change loses UI state** (rotation, dark mode) → `rememberSaveable` or ViewModel; not plain `remember`.
- **`mutableStateOf` for a list mutated in place** doesn't trigger recompose. Fix: `mutableStateListOf` or assign a new list (`list = list + item`).
- **Modifier order bug** (click area, padding, background misaligned). Fix: order `.clickable` before `.padding` for full touch target; reason about chain top-down.
- **Room schema change without migration** → crash on upgrade. Fix: write `Migration`, bump `version`, test upgrade.
- **StateFlow default value flashes** before real data. Fix: model `Loading` in a sealed UiState, render accordingly.
- **`by remember { mutableStateOf }` recreated because it's above the state it depends on**, or state read in the wrong scope. Fix: hoist correctly; keep the read where recompose should happen.
- **kapt slow / breaks with newer Kotlin**: Fix: migrate annotation processors to **KSP** (Room, Hilt, Moshi support it).
- **Compose preview crashes** on ViewModel/Hilt/real data. Fix: pass state directly to a stateless composable; use `@PreviewParameter` with fake data.
- **Coroutine launched in `GlobalScope`** outlives the screen, leaks. Fix: always use a lifecycle-bound scope (`viewModelScope`/`lifecycleScope`/`rememberCoroutineScope`).
- **Configuration change re-triggers `LaunchedEffect`** doing a one-shot (re-fetch/re-navigate). Fix: key it on a stable id / `Unit`, or move to ViewModel init / a consumed event.
