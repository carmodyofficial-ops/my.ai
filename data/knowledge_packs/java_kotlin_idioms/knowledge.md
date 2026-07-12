# Java + Kotlin Idioms

## Java — data & control
- **Records**: `record Point(int x,int y){}` — final, immutable, auto `equals`/`hashCode`/`toString`, accessors `x()` not `getX()`. Add compact canonical ctor for validation: `record Range(int lo,int hi){ Range{ if(lo>hi) throw new IllegalArgumentException(); } }`. Records can implement interfaces, not extend.
- **Sealed**: `sealed interface Shape permits Circle,Square{}` — closes the hierarchy; permitted types must be `final`/`sealed`/`non-sealed`. Enables exhaustive switch with no `default`.
- **Switch patterns** (21+): `switch(s){ case Circle c -> c.r(); case Square s when s.side()>0 -> ...; case null -> 0; default -> -1; }`. Arrow = no fall-through, no break. `case null` must be explicit or switch NPEs on null. Record deconstruction: `case Point(int x,int y) -> x+y`.
- **var**: locals only, RHS type obvious. Not fields/params/returns. `var l = new ArrayList<String>();` fine; `var x = null;` illegal.

## Java — streams / Optional
- **Streams**: `list.stream().filter(X::ok).map(X::name).collect(toList())`. Lazy; terminal op triggers. A stream is single-use — reusing throws `IllegalStateException`.
- Collectors: `groupingBy(X::type)`, `groupingBy(X::type, counting())`, `toMap(k,v)` (throws on dup key — supply merge fn), `joining(", ")`, `partitioningBy(pred)`, `mapping`, `teeing`.
- Primitive streams `IntStream`/`LongStream` avoid boxing: `.sum()`, `.average()`, `range(0,n)`, `.boxed()` to re-box. `mapToInt(X::size)`.
- `flatMap` flattens nested; `reduce(identity, acc)`; `takeWhile`/`dropWhile`/`iterate` (9+). `Stream.of`, `Arrays.stream`, `Collection.stream`.
- No side effects in `map`/`filter`; use `forEach` for effects. `parallelStream()` only for CPU-bound, large, stateless work — never shared mutable state.
- **Optional**: return type only, never field/param/collection element. `opt.map(..).orElseGet(this::calc)`; avoid `.get()`; `orElseThrow()`. `orElse` always evaluates its arg — use `orElseGet` for expensive defaults.

## Java — concurrency
- **Virtual threads** (21+): `Executors.newVirtualThreadPerTaskExecutor()` — cheap, one per blocking task; don't pool them. Pinning: avoid `synchronized` around blocking I/O (use `ReentrantLock`).
- `CompletableFuture.supplyAsync(sup,exec).thenApply(f).thenCompose(g).exceptionally(h)`. `thenApply` = sync map, `thenCompose` = flatMap for nested futures.
- Platform threads: `ExecutorService` + `submit`, always `shutdown()` (try-with-resources on 19+). Never `new Thread` per task.
- Prefer `java.util.concurrent`: `ConcurrentHashMap`, `AtomicLong`, `BlockingQueue` over manual `synchronized`.

## Java — collections / generics
- `List.of()`/`Map.of()`/`Set.of()` immutable, reject null. `List.copyOf(c)` defensive copy. Modifying these throws `UnsupportedOperationException`.
- **PECS**: `List<? extends T>` to read (producer), `List<? super T>` to write (consumer). `<?>` unbounded read-only.
- `equals`/`hashCode`: override both together; equal objects must have equal hashes. Include same fields in both; keep consistent with `compareTo`.
- try-with-resources: `try(var in=open(); var out=create()){...}` — closes in reverse order, even on exception; suppressed exceptions attached.

## Kotlin — core
- **Null safety**: `String?` nullable; `a?.b`, `a ?: default`, `a?.let{...}`. `!!` throws — a smell; refactor. Safe cast `as?` returns null on mismatch.
- **Data/sealed**: `data class User(val id:Int,val name:String)` — `equals`/`hashCode`/`copy`/`componentN`. `sealed interface Result` + `data class Ok`/`Err` → exhaustive `when` (no `else`).
- `val` by default, `var` only when reassigned. `const val` compile-time.
- **when**: `when(x){ is A->..; in 1..9->..; else->.. }` as expression (must be exhaustive). Subject-less `when{ cond-> }` replaces if/else chains.
- **Extensions**: `fun String.slug()=lowercase().replace(" ","-")` — statically dispatched (no override). Extension props: `val List<*>.mid get()=this[size/2]`.
- **Scope fns**: `let` (nullable map, returns lambda), `apply` (config, returns receiver), `also` (side-effect, returns receiver), `run`/`with` (block result), `takeIf`/`takeUnless` (conditional).
- **Delegation**: `class C(b:Base):Base by b`; `by lazy{}` (thread-safe once), `by Delegates.observable()`, `val x by map`, `by viewModels()`.
- Prefer expression bodies: `fun sq(x:Int)=x*x`. Trailing lambda: `items.filter{it.ok}`. Named/default args kill overload explosion: `fun f(a:Int,b:Int=0,c:String="")`.
- `typealias` for complex types; `value class Meters(val v:Double)` (inline, no wrapper allocation at runtime).

## Kotlin — coroutines / Flow
- `suspend fun` only callable from coroutine/suspend. `launch{}` fire-and-forget (returns `Job`), `async{}.await()` for a result (`Deferred`).
- Structured concurrency: `coroutineScope{}` waits for all children; one child failure cancels siblings. Never `GlobalScope`.
- `withContext(Dispatchers.IO)` for blocking I/O; `Default` for CPU. Suspend fns must be cancellation-cooperative (`ensureActive()`/`isActive`).
- **Flow**: cold async stream. `flow{ emit(x) }.map{}.filter{}.collect{}`. `StateFlow`/`SharedFlow` are hot. `flowOn(Dispatchers.IO)` shifts upstream context. `catch{}` operator, `onEach`, `debounce`, `combine`, `flatMapLatest`.
- `supervisorScope`: a child failure doesn't cancel siblings (independent tasks). `Job`/`SupervisorJob` in a scope; `cancel()`/`join()`. `Mutex`/`Semaphore` (suspend, non-blocking) over `synchronized`.
- `runBlocking{}` bridges blocking→suspend at `main`/test boundaries only — never inside a coroutine.

## Gotchas -> Fix
- Java `==` compares references -> use `.equals()`; intern-cached `Integer` (-128..127) makes `==` sometimes work, masking the bug.
- Autoboxing in hot loops (`Long`/`Integer`) -> use primitives/`IntStream`; `Map<Integer,..>` boxing is unavoidable but keep keys small-cached.
- Mutable `static`/shared collection -> defensive copy at API boundary (`List.copyOf`) or return `unmodifiableList`.
- Returning `null` from a stream `map` then `.orElse` chaining -> keep `Optional` end-to-end; don't unwrap early.
- Reusing a consumed stream -> build a fresh stream each terminal op; keep the source collection, not the stream.
- `Optional.get()` without `isPresent()` -> `orElseThrow`/`map`/`orElseGet`.
- Checked exceptions inside lambdas won't compile -> wrap in unchecked, or use a throwing-functional-interface helper.
- Kotlin **platform types** (`String!` from unannotated Java) bypass null checks -> assert/annotate at the seam; add `@Nullable`/`@NotNull` to Java or `requireNotNull`.
- Capturing a mutable `var` in a Kotlin lambda/coroutine -> capture a `val` snapshot; loop index closures capture by reference otherwise.
- Kotlin `data class` `copy()` skips init-block validation -> validate in a factory/`init` won't rerun; make ctor private + factory.
- `!!` on platform/nullable -> `?:`/`requireNotNull(x){"msg"}` for a meaningful message.
- Coroutine launched in `GlobalScope` leaks past its owner -> tie to a lifecycle `CoroutineScope`; use `coroutineScope`/`supervisorScope`.
- Blocking call inside a coroutine on `Default` starves the pool -> `withContext(Dispatchers.IO)`.
- `Flow.collect` in `launch` without cancellation -> collect in a scope that cancels; use `stateIn`/`shareIn` with `SharingStarted`.
- Kotlin `lateinit` accessed before init -> `UninitializedPropertyAccessException`; guard with `::x.isInitialized` or use nullable + `?:`.
- Java `finalize`/manual close forgotten -> try-with-resources; implement `AutoCloseable`.
- `equals` without matching `hashCode` -> broken `HashMap`/`HashSet` lookups (object "vanishes"); override both.

## Java — more idioms
- **Text blocks**: `"""\n  {"k":1}\n  """` — multi-line, incidental leading whitespace stripped to the closing delimiter's indent; `\` line-continuation, `\s` trailing space.
- **Pattern instanceof**: `if (o instanceof String s && !s.isBlank()) use(s);` — binds and flows the type.
- Enums are full classes: per-constant bodies, fields, `EnumMap`/`EnumSet` (bit-set fast). `valueOf` throws on bad name.
- Prefer composition; program to interfaces (`List` not `ArrayList` in signatures). `Comparator.comparing(X::a).thenComparing(X::b).reversed()`.
- `Objects.requireNonNullElse`, `Objects.equals`, `Objects.hash(a,b)` for null-safe helpers.
- Strings immutable + interned literals; `StringBuilder` in loops (`+` in a loop is O(n²)). `String.format`, text blocks, `str.repeat`/`strip`/`isBlank` (11+).
- `Comparable` natural order (`compareTo`), keep consistent with `equals`. `List.sort(cmp)`, `Collections.sort`. `NavigableMap`/`TreeMap` for range queries.
- Don't catch `Exception`/`Throwable` broadly; never swallow — log or rethrow. Never catch `InterruptedException` without restoring the flag (`Thread.currentThread().interrupt()`).

## Kotlin — more idioms
- `inline fun` for lambda params (no allocation, enables non-local `return`); `reified` type params keep the type at runtime: `inline fun <reified T> parse(s:String):T`.
- **Sequences**: `list.asSequence().map{}.filter{}.first()` — lazy, one pass, no intermediate lists; use for long chains/large data. Eager `list.map{}` allocates each step.
- Variance: `out T` (covariant, producer), `in T` (contravariant, consumer) at declaration site; `*` star-projection.
- `object` singleton; `companion object` for factory/statics; `data object` for stateless sealed cases.
- Destructuring: `val (id,name)=user`; `for ((k,v) in map)`. Operator overloading via `operator fun plus`/`get`/`invoke`.
- `require`/`check`/`error` for preconditions; `runCatching{}` → `Result<T>`. String templates `"$x ${y.z}"`, raw `"""..."""`.
- Interop: `@JvmStatic`, `@JvmOverloads` (generate Java overloads for default args), `@JvmField`, `@Throws` for checked-exception visibility.

## JVM / build
- GC: default **G1** (balanced); **ZGC**/**Shenandoah** for low-pause large heaps; **Parallel** for max throughput/batch. Tune `-Xmx`/`-Xms` equal to avoid resize pauses. Heap = objects; stack = frames/primitives/refs. Escape analysis may stack-allocate short-lived objects.
- OOM sources: unbounded caches, `ThreadLocal` leaks (esp. on pooled threads), listener/classloader leaks; take a heap dump (`jmap -dump`/`jcmd`), analyze with MAT/Eclipse.
- JIT (C1/C2) warms up hot methods; benchmark with **JMH**, not naive loops (dead-code elimination lies).
- `String` interning + `==`: literals pooled; `new String("x")` isn't — always `.equals`.
- **Gradle** (`build.gradle.kts`): `implementation` (not exposed to consumers) vs `api` (transitive) vs `testImplementation`/`runtimeOnly`; version catalogs (`libs.versions.toml`); daemon + build cache. **Maven** (`pom.xml`): `<scope>` compile/provided/test/runtime/system; BOM via `<dependencyManagement>`; lifecycle phases validate→compile→test→package→install→deploy.
