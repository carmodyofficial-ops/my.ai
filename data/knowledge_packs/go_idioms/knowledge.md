# Go Idioms (dense)

## Errors
- Check immediately: `if err != nil { return ..., err }`. Don't discard with `_` unless deliberate.
- Wrap with context: `fmt.Errorf("read %s: %w", name, err)` — `%w` wraps (keeps chain for `Is`/`As`), `%v` flattens (breaks it). Wrap at each layer, but wrap once — don't log **and** return (double noise); handle at the top.
- Sentinels: `var ErrNotFound = errors.New("not found")`; test with `errors.Is(err, ErrNotFound)`. Custom types: `var e *MyErr; errors.As(err, &e)` unwraps to a concrete type.
- Return early; keep the happy path un-indented at the left margin. Errors are values — no exceptions.

## Naming / style
- Short names for short scopes (`i`, `r`, `buf`); package name is part of the identifier — avoid stutter (`http.Server`, not `http.HTTPServer`). Exported = Capitalized. One-method interfaces named `-er` (`Reader`, `Stringer`). Getters drop `Get` (`u.Name()`, not `u.GetName()`). Return errors as the last value.
- Prefer many small files over one huge; group by responsibility. `gofmt` is non-negotiable (tabs, canonical layout).

## Concurrency: goroutines / channels / select
- `go f()` starts a goroutine; **ensure it can exit** or it leaks (blocked forever on a channel/ctx). Every goroutine needs a defined stop condition.
- Channels: **sender** closes, never the receiver. `for v := range ch` drains until closed. Send on a closed channel panics; receive from closed returns zero value + `ok=false` (`v, ok := <-ch`).
- Unbuffered `ch <- x` blocks until a receiver is ready (synchronization point). No reader / main exits = deadlock. Buffered `make(chan T, n)` blocks only when full.
- `select` multiplexes; `default` makes it non-blocking:
```go
select {
case v := <-ch:      use(v)
case <-ctx.Done():   return ctx.Err()
case <-time.After(d): return ErrTimeout
default:             // non-blocking fallthrough
}
```
- Nil channel blocks forever (useful to disable a `select` case). Signal-only channel: `chan struct{}` (zero-size).

## Context
- Always pass `ctx context.Context` as the **first** arg; never store it in a struct. Derive: `ctx, cancel := context.WithTimeout(parent, 5*time.Second); defer cancel()` (always `defer cancel()` even on success — avoids leak).
- `ctx.Done()` returns a channel closed on cancel/timeout; `ctx.Err()` says why (`context.Canceled`/`DeadlineExceeded`). Use `context.Value` only for request-scoped metadata, not params.

## sync primitives
- `mu.Lock(); defer mu.Unlock()`. Use `sync.RWMutex` when reads dominate (`RLock`). Never copy a struct that holds a `Mutex`/`WaitGroup` (copies the lock state) — pass by pointer; `go vet` catches this.
- `wg.Add(1)` **before** `go`, `defer wg.Done()` inside the goroutine, `wg.Wait()` after. `sync.Once` for one-time init: `once.Do(fn)`. `atomic.AddInt64`/`atomic.Value` for lock-free counters. `errgroup.Group` to run goroutines and collect the first error.

## Interfaces
- Accept interfaces, return concrete structs. Keep interfaces small — 1–3 methods (`io.Reader`, `io.Writer`, `error`, `fmt.Stringer`). Define interfaces in the **consumer** package, not the producer.
- Interfaces are satisfied implicitly (structural) — no `implements` keyword. `var _ MyIface = (*MyType)(nil)` asserts satisfaction at compile time.
- Type switch: `switch v := x.(type) { case int: ...; case string: ... }`. Assertion with ok: `v, ok := x.(T)`.

## Slices / maps / structs
- Slice = ptr + len + cap over a backing array. `append` grows; may reuse or reallocate the array → aliasing hazard.
- `make([]T, 0, n)` preallocates cap (avoids repeated realloc). Distinguish `nil` vs empty slice; `len(nil) == 0`, `range nil` is fine, `append(nil, x)` works.
- Maps: write to a `nil` map **panics** — `m := map[K]V{}` or `make(map[K]V)` first. Read from nil is fine (zero value). Comma-ok: `v, ok := m[k]`. Iteration order is randomized — sort keys for determinism. `delete(m, k)`.
- Struct embedding for composition: `type Server struct{ *log.Logger }` promotes `Logger`'s methods. Lean on zero values: `var mu sync.Mutex`, `var b bytes.Buffer` — usable without init.

## defer
- Runs at **function** return (LIFO), not block end. In a loop, deferred closes pile up until the function exits → extract the body to a helper or close explicitly. Deferred args are evaluated at the `defer` statement; `defer f(x)` captures `x` now, but `defer func(){ use(x) }()` sees the final value. Use `defer` to `recover()` from panics.

## Generics (1.18+)
- `func Map[T, U any](s []T, f func(T) U) []U`. Constraints: `any`, `comparable` (for map keys/`==`), or interface unions `[T int | float64]`. Use `constraints.Ordered` (golang.org/x/exp) for `<`. Prefer concrete types / interfaces when generics add no clarity.

## Modules
- `go mod init module/path`, `go mod tidy` (prune+add deps), `go get pkg@version`, `go build ./...`. Import path = module path + dir. Capitalized identifiers are exported (package-level and struct fields). `go vet`, `staticcheck`, `go test -race` in CI. `internal/` packages are importable only within the module.

## Idiomatic patterns
- Functional options for optional config: `func WithTimeout(d) Option { return func(c *Config){ c.timeout = d } }`, apply variadic in constructor. Cleaner than many-arg constructors or a big config struct.
- Named returns for `defer`-based mutation (e.g. `recover` setting `err`); otherwise prefer explicit returns for clarity.
- `iota` for enums: `const ( A = iota; B; C )`. Add a `String()` method (or `stringer`) for printable enums.
- Comparable structs work as map keys / with `==`; structs with slices/maps/funcs don't (`==` won't compile). Use `reflect.DeepEqual` or `slices.Equal`/`maps.Equal` (1.21+) for deep comparison.
- `time.Time`: compare with `.Before`/`.After`/`.Equal`, not `==` (monotonic clock + location differ). Durations are typed: `5 * time.Second`.
- Prefer `strings.Builder` over `+=` in loops (avoids O(n²) copies); `bytes.Buffer` for `[]byte`. Pre-size with `.Grow(n)`.

## GOTCHAS → fix
- **Loop var capture (pre-1.22)**: `for _, v := range xs { go func(){ use(v) }() }` — all goroutines see the last `v`. Fix: `v := v` shadow, pass as arg `go func(v T){}(v)`, or Go 1.22+ (per-iteration var).
- **nil interface != nil**: a typed nil pointer stored in an `error`/`interface{}` is non-nil (has a type). Returning `var p *T; return p` as `error` fails `== nil`. Return literal `nil`.
- **Slice aliasing**: `append` may share the backing array — mutations leak between slices, and appending to a sub-slice can overwrite the parent. Copy when retaining: `b := append([]T(nil), a...)` or `slices.Clone(a)`. Full-slice expr `a[low:high:max]` caps to force realloc.
- **Goroutine leak**: goroutine blocked on a channel/`ctx` that never fires never exits → memory + fd growth. Give every goroutine a cancel path (`ctx`, closed channel, or a bounded send).
- **Unbuffered channel deadlock**: sending with no ready receiver (or receiving with no sender) blocks forever → `fatal error: all goroutines are asleep`. Buffer, or run the peer in its own goroutine.
- **Loop-defer resource pileup**: FDs/locks accumulate — see `defer` above.
- **Map concurrent access**: concurrent read+write panics (`fatal error: concurrent map...`) — guard with a mutex or use `sync.Map`.
- **Shadowing with `:=`**: `x, err := f()` then `x, err := g()` in an inner block silently shadows the outer `err` → bug where the outer never sees the error. `go vet -vettool=shadow` / careful `=` vs `:=`.
- **Range copies**: `for _, v := range structs { v.X = 1 }` mutates a copy — index instead: `for i := range structs { structs[i].X = 1 }`.
- **Integer division truncates**: `5/2 == 2`; convert to float first `float64(a)/float64(b)`. No implicit numeric conversion — `int32 + int64` won't compile.
- **`defer` in hot loops** has per-call overhead and delays cleanup — inline cleanup when it matters.
- **Comparing errors with `==`** breaks once wrapped — use `errors.Is`, not `err == ErrX`.
- **Unhandled goroutine panic** crashes the whole process (no per-goroutine recovery from outside) — `recover()` must run in the panicking goroutine's own `defer`.

## Tests
- Table-driven + subtests, `t.Helper()` in assert helpers, `t.Cleanup()` for teardown:
```go
for _, tc := range cases {
  t.Run(tc.name, func(t *testing.T){
    if got := F(tc.in); got != tc.want {
      t.Errorf("F(%v)=%v want %v", tc.in, got, tc.want)
    }
  })
}
```
