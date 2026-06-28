# C# / .NET Idioms

## LINQ
- `Where`/`Select`/`First`/`FirstOrDefault`/`Any`/`All`. Use `Any()` not `Count() > 0`.
- Deferred: query runs on enumeration. `.ToList()`/`.ToArray()` to materialize.
- `First` throws if empty; `FirstOrDefault` returns default. `Single` asserts exactly one.

## Async
- `async Task`/`Task<T>`; `await` instead of `.Result`/`.Wait()` (deadlocks on UI/ASP contexts).
- Library code: `await foo.ConfigureAwait(false)`.
- No `async void` except event handlers (exceptions go unobserved → crash).
- `await Task.WhenAll(t1, t2)` to parallelize.

## Types
- Auto-props: `public int Id { get; init; }`. `init` = set only in initializer.
- Records: `public record Point(int X, int Y);` — value equality, `with` clone.
- Expression-bodied: `public int Area => W * H;`, `void Log(string m) => _l.Info(m);`

## Nullable refs
- `<Nullable>enable</Nullable>`. `string?` may be null; `string` shouldn't.
- `x?.Prop`, `x ?? fallback`, `x!.M()` (suppress, asserts non-null).

## Pattern matching
```csharp
var label = shape switch {
    Circle c => $"r={c.R}",
    Rect { W: 0 } => "empty",
    null => "none",
    _ => "other"
};
if (o is string s && s.Length > 0) { }
```

## Disposal
- `using var f = File.OpenRead(p);` disposes at scope end. `await using` for `IAsyncDisposable`.
- Always dispose streams/connections/`HttpClient` content.

## Generics
- `T Max<T>(T a, T b) where T : IComparable<T>` — constrain with `where`. Also `class`, `struct`, `new()`, `notnull`.

## Strings
- `$"Hello {name}, {count:N0}"`. Use `StringBuilder` in loops.

## DI
- Constructor injection; register `AddScoped`/`AddSingleton`/`AddTransient`. Depend on interfaces.

## API surface
- Return `IEnumerable<T>`/`IReadOnlyList<T>`; expose `List<T>` only when caller mutates.

## Gotchas
- `async void` → unobserved exceptions, can't await.
- `.Result`/`.Wait()` → deadlock; always `await`.
- Forgetting `using`/`Dispose` → leaks.
- Re-enumerating a deferred query reruns it; materialize once with `ToList()`.
- Mutable structs: copies mutate, not original. Make structs `readonly`.
- `==` on reference types compares identity, not value; override `Equals`/use records.
- Capturing loop variable in closures: copy to a local (`var x = i;`) before capturing.
