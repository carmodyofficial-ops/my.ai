# C# / .NET Idioms

## Async / await
- `async Task`/`async Task<T>`; `await` — never `.Result`/`.Wait()` (deadlocks on UI/legacy ASP.NET sync contexts; ASP.NET Core has no context but still block a thread).
- **`async void` only for event handlers** — its exceptions can't be awaited and crash the process; everything else returns `Task`.
- Library code: `await x.ConfigureAwait(false)` — don't resume on the captured context. App/ASP.NET Core code doesn't need it.
- Parallelize independent work: `await Task.WhenAll(t1,t2)`; `WhenAny` for first-done/timeout. Don't `await` in a loop when tasks are independent.
- Flow `CancellationToken` end-to-end; `ct.ThrowIfCancellationRequested()`. `ValueTask<T>` for hot paths that usually complete synchronously — await once, don't store/await twice.

## LINQ
- `Where`/`Select`/`First`/`FirstOrDefault`/`Any`/`All`/`Single`. Use `Any()` not `Count()>0` (stops at first).
- **Deferred execution**: the query runs on each enumeration, capturing current variables. Materialize once with `ToList()`/`ToArray()`.
- `First` throws if empty; `FirstOrDefault` returns `default`; `Single` asserts exactly one (throws otherwise). `SingleOrDefault` = 0 or 1.
- `Select` projects, `SelectMany` flattens, `GroupBy` → `IGrouping`, `ToDictionary` throws on dup key. `OrderBy(...).ThenBy(...)`.
- Aggregation: `Sum`/`Min`/`Max`/`Average`/`Count`/`Aggregate`. `Zip`, `Chunk`, `DistinctBy`/`MaxBy`/`MinBy` (net6+), `Skip`/`Take`/`TakeWhile`. `SequenceEqual` for element compare.
- Query vs method syntax equivalent; method syntax is more complete. Prefer `AsEnumerable()` to intentionally switch EF→LINQ-to-objects at a boundary.
- IQueryable (EF) translates to SQL — a client-only method inside breaks translation; project to a DTO before leaving the query.

## Types — records / structs / init
- **Records**: `public record Point(int X,int Y);` — value equality, `with` non-destructive copy, deconstruct, `ToString`. `record struct` for value-type semantics. `record` uses reference equality's opposite: structural.
- `init` accessors: `public int Id { get; init; }` — settable only in object initializer/ctor. `required` forces the initializer to set it: `public required string Name { get; init; }`.
- Struct = value type (copied on assign/pass, lives on stack/inline); class = reference type (heap, GC). Make structs **`readonly struct`** to prevent defensive copies; keep them small (≤16 bytes) or pass `in`/`ref`. `ref struct` (like `Span`) is stack-only.
- `enum` backed by int; `[Flags]` for bit sets (`Color.Red | Color.Blue`, powers of two). `default`/`default(T)` for the zero value; nullable value types `int?` = `Nullable<int>` (boxes to null or the value).
- `Span<T>`/`ReadOnlySpan<T>`: stack-only view over array/stackalloc/string, zero-copy slicing (`s.AsSpan(2,4)`). Can't be a field of a class, boxed, or used across `await`.

## Nullable reference types
- `<Nullable>enable</Nullable>`. `string?` may be null; `string` shouldn't (compiler warns on deref/assign).
- `x?.Prop`, `x ?? fallback`, `x ??= init`, `x!.M()` (null-forgiving — asserts, suppresses warning; use sparingly).
- Attributes: `[NotNull]`, `[MaybeNull]`, `[NotNullWhen(true)]` on `TryGet` patterns.

## Pattern matching
```csharp
var label = shape switch {
    Circle { R: >0 and <10 } c => $"r={c.R}",
    Rect (var w, var h) when w==h => "square",
    null => "none",
    _ => "other"
};
if (o is string { Length: >0 } s) { }          // type + property + capture
```
Relational (`>`, `<`), logical (`and`/`or`/`not`), list (`[1, .., var last]`), positional patterns. Switch expr must be exhaustive or add `_`.

## Disposal
- `using var f = File.OpenRead(p);` disposes at scope end; `await using` for `IAsyncDisposable`.
- Always dispose streams/connections/`DbContext`. **`HttpClient` is the exception** — reuse a single instance (or `IHttpClientFactory`); disposing per-request exhausts sockets.
- `IDisposable` on a type with unmanaged resources → implement the full dispose pattern; `SafeHandle` avoids finalizers.

## Collections / DI / strings
- API surface: return `IEnumerable<T>`/`IReadOnlyList<T>`; expose `List<T>` only when the caller must mutate. `IReadOnlyDictionary`, `FrozenSet`/`FrozenDictionary` (read-heavy).
- **DI**: constructor injection; `AddSingleton` (one, thread-safe), `AddScoped` (per request), `AddTransient` (per resolve). Never inject a **scoped into a singleton** (captured dependency — stale/disposed). Depend on interfaces.
- Strings: `$"{name}, {count:N0}"`; `StringBuilder` in loops (`+` concat is O(n²)); `string.Create`/`Span` for hot formatting; raw string literals `"""..."""`. Strings are immutable + interned literals.
- Concurrent collections: `ConcurrentDictionary`/`ConcurrentQueue`/`ConcurrentBag` for shared state; `Channel<T>` for producer/consumer; `Interlocked` for atomic counters; `lock(obj)` for critical sections (never `lock` on `this`/`string`/public objects).

## Gotchas -> Fix
- **`async void`** -> unobserved exceptions crash the app; only for event handlers, else return `Task`.
- **`.Result`/`.Wait()`/`.GetAwaiter().GetResult()`** on async -> deadlock/thread starvation; `await` all the way up.
- **Missing `ConfigureAwait(false)`** in a library called from a sync-context host -> deadlock; add it in library code.
- **LINQ multiple enumeration**: passing `IEnumerable<T>` and calling `.Count()` then `.Where()` re-runs the source (DB round-trips, side effects) -> `ToList()` once.
- **Deferred query captures a loop variable** -> the query sees the final value; materialize inside the loop or capture a local.
- **Mutable struct surprise**: `list[0].X = 5` on `List<struct>` mutates a copy (won't compile / no-ops via property) -> use `readonly struct` + `with`, or a class.
- **Boxing**: storing a struct in `object`/non-generic collection, or a struct implementing an interface called via the interface, allocates + copies -> use generics (`List<T>`), constrain `where T:struct`, avoid `object`.
- **`==` on reference types** compares identity, not value -> override `Equals`/`GetHashCode` together, or use a `record`.
- **Overriding `Equals` without `GetHashCode`** -> broken `Dictionary`/`HashSet` lookups; override both, keep consistent.
- **Capturing `CancellationToken`/`ct` not passed down** -> operations don't cancel; thread `ct` through every async call.
- **`Span<T>` across `await`/`yield`** -> won't compile (ref struct); copy out what you need first.
- **`DateTime.Now`** in domain logic -> timezone/DST bugs; use `DateTimeOffset.UtcNow` / `TimeProvider` (injectable for tests).
- **`float`/`double` for money** -> rounding errors; use `decimal`.
- **String `==` culture surprise**: default `==` is ordinal, but `ToUpper`/`Compare` are culture-sensitive -> `StringComparison.Ordinal`/`OrdinalIgnoreCase` explicitly.
- **EF: client-side evaluation** from an untranslatable expression -> silent full-table load; project early, keep queries translatable.
- **Fire-and-forget `Task` unawaited** -> exceptions lost, may crash on finalize -> await it, or explicitly observe (`_ = t.ContinueWith(...)`) and log.
- **Scoped service in singleton** -> captured/disposed dependency; inject `IServiceScopeFactory` and create a scope per unit of work.

## More C# idioms
- **Collection expressions** (C# 12): `int[] a = [1,2,3];`, `List<int> l = [..a, 4];` spread. Target-typed `new()`: `Point p = new(1,2);`.
- **Primary constructors** (C# 12) on classes: `class Svc(ILogger log){ ... }` — params in scope for the body.
- Tuples: `(int x,int y) Get() => (1,2);` value tuples (struct), deconstruct `var (x,y)=Get();`. Named for clarity.
- `nameof(x)` for refactor-safe names; `[CallerMemberName]` for property-change/logging. `is not null`/`is null` over `== null` (can't be operator-overloaded away).
- `switch` statements + expressions; `goto case`/relational patterns. `params` + now `params Span<T>` (C# 13). Local functions over private helpers when scoped.
- Iterators: `yield return` builds a lazy `IEnumerable<T>` (deferred, resumable). `IAsyncEnumerable<T>` + `await foreach` for async streams; add `.WithCancellation(ct)`.
- Extension methods: `static T M(this X x,...)` in a static class; enables LINQ. Prefer over util classes for discoverability.
- `Enumerable`/`Span` for zero-alloc; `stackalloc Span<byte>` small buffers; `ArrayPool<T>.Shared.Rent`.

## .NET runtime
- **GC**: generational (Gen0/1/2 + LOH ≥85KB). Short-lived allocations are cheap (Gen0); avoid promoting garbage to Gen2. Server GC (throughput, per-core heaps) vs Workstation GC. Minimize allocations in hot paths (`Span`, pooling, `struct`).
- Value types live inline/on stack (no GC); reference types on the managed heap. Boxing moves a value type to the heap.
- `Task` = future/promise, scheduled on the thread pool; `async` is a state machine, not a new thread. `Task.Run` offloads CPU work to the pool — don't wrap already-async I/O in it.
- **Source generators** (`[GeneratedRegex]`, `System.Text.Json` `JsonSerializerContext`, `LoggerMessage`) emit code at compile time — no reflection, AOT-friendly, faster startup.
- Equality: value types compare field-by-field (via `ValueType.Equals`, reflection-slow unless overridden); reference types compare identity. `IEquatable<T>` avoids boxing in generic collections.
- Exceptions: throw specific types; don't use for control flow (expensive). `try`/`catch (SpecificEx)`/`finally`; filter `catch (Ex e) when (e.Code==5)`. `using`/`finally` for cleanup; never swallow silently.

## Build / tooling
- SDK-style `.csproj`: `<TargetFramework>net9.0</TargetFramework>`, `<Nullable>enable</Nullable>`, `<ImplicitUsings>enable</ImplicitUsings>`, `<TreatWarningsAsErrors>`. `dotnet build`/`test`/`run`/`publish`.
- `PackageReference` for NuGet; central package management via `Directory.Packages.props`. `<LangVersion>` to opt into newer C#.
- AOT/trimming: `<PublishAot>` — reflection/dynamic-code breaks; use source generators. `analyzers` + Roslyn analyzers for style/correctness at build.
