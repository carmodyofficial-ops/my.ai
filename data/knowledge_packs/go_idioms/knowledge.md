# Go Idioms (dense)

## Errors
- Check immediately: `if err != nil { return ..., err }`. Don't discard with `_`.
- Wrap with context: `fmt.Errorf("read %s: %w", name, err)` (use `%w`, not `%v`).
- Sentinels: `var ErrNotFound = errors.New("not found")`; test with `errors.Is(err, ErrNotFound)`. Types: `errors.As(err, &target)`.
- Add context at each layer; don't log+return (double noise). Handle once.

## Concurrency
- `go f()` starts a goroutine; ensure it can exit (else leak).
- Channels: sender closes, never receiver. `for v := range ch` drains until close.
- Unbuffered `ch<-` blocks until a receiver — main exiting / no reader = deadlock. Buffer or run reader in own goroutine.
- `select { case v:=<-ch: ; case <-ctx.Done(): return ctx.Err() }` for cancel/timeout.
- Always pass `ctx context.Context` first arg; derive `ctx,cancel:=context.WithTimeout(...)`; `defer cancel()`.

## GOTCHAS
- **Loop var capture** (pre-1.22): `for _,v:=range xs { go func(){ use(v) }() }` all see last `v`. Fix: `v:=v` shadow, or pass as arg, or Go 1.22+.
- **nil interface != nil**: returning a typed nil pointer as `error`/`interface{}` is non-nil. Return literal `nil`.
- **Slice aliasing**: `append` may share or reallocate backing array — mutations leak between slices. Copy when retaining: `b:=append([]T(nil), a...)`.
- **Map**: write to nil map panics — `m:=map[K]V{}` first. Read OK. Use comma-ok: `v,ok:=m[k]`.
- **loop-defer**: `defer` runs at function (not block) end — in a loop, FDs pile up. Extract to a func or close explicitly.

## Style
- Accept interfaces, return concrete structs. Keep interfaces small (1-3 methods, e.g. `io.Reader`).
- Embed for composition: `type Server struct{ *log.Logger }`.
- Lean on zero values: `var mu sync.Mutex`, `var wg sync.WaitGroup`, `var b bytes.Buffer` — ready to use.
- Distinguish nil vs empty slice; `len()` works on nil. Preallocate `make([]T,0,n)` when size known.

## sync
- `mu.Lock(); defer mu.Unlock()`. Don't copy a struct holding a Mutex.
- `wg.Add(1)` before `go`, `defer wg.Done()` inside, `wg.Wait()`.

## Tests
- Table-driven + subtests:
```go
for _, tc := range cases {
  t.Run(tc.name, func(t *testing.T){
    if got := F(tc.in); got != tc.want {
      t.Errorf("F(%v)=%v want %v", tc.in, got, tc.want)
    }
  })
}
```
- Use `t.Helper()` in assert helpers; `t.Cleanup()` for teardown.
