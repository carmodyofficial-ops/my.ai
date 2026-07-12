# Rust Idioms

## Ownership / borrowing / lifetimes
- One owner; value moves on assign/pass. `let b = a;` invalidates `a` for non-`Copy` types (`String`, `Vec`, `Box`). `Copy` types (`i32`, `bool`, `&T`, `char`) duplicate bitwise instead.
- Borrows: `&T` shared (many at once, read-only), `&mut T` exclusive (exactly one, no other borrow live). This is the aliasing-XOR-mutation rule enforced at compile time.
- Non-lexical lifetimes: a borrow ends at its **last use**, not end of scope — so `let r = &x; use(r); x = 5;` compiles.
- `clone()` is explicit and visible. If you clone to dodge the borrow checker, restructure instead: narrow scopes, split borrows (borrow distinct fields separately), pass `&`, or return owned data.
- Lifetimes name how long a reference is valid; usually **elided**. Annotate only to tie an output ref to an input: `fn first<'a>(s: &'a str) -> &'a str`. Struct holding a ref needs `struct S<'a> { r: &'a T }`. `'static` = lives for whole program (string literals, owned leaked data).

## Collections / stdlib reach-for
- `Vec<T>` growable array; `VecDeque<T>` double-ended; `HashMap<K,V>`/`BTreeMap` (sorted); `HashSet`/`BTreeSet`; `BinaryHeap` (max-heap). `entry` API: `map.entry(k).or_insert_with(Vec::new).push(v)` avoids double lookup.
- `slices`/`iterator` helpers: `.sort()`, `.sort_by_key()`, `.dedup()`, `.contains()`, `.binary_search()`, `.retain(|x| ...)`, `.chunks()`, `.windows()`.

## Result / Option + `?`
- `?` propagates `Err`/`None` early: `let f = File::open(p)?;`. In a fn returning `Result`, `?` on `Err` returns it; the error type must convert via `From` (that's what `anyhow`/`Box<dyn Error>` and `thiserror` `#[from]` enable).
- No `unwrap()`/`expect()` in production paths. Use `?`, or `.expect("invariant: X holds because Y")` only when truly impossible. `unwrap()` on `Err`/`None` panics.
- Combinators: `opt.map(f)`, `.unwrap_or(d)`, `.unwrap_or_else(|| ...)`, `.unwrap_or_default()`, `.ok_or(e)?`, `res.ok()`, `.map_err(f)`, `and_then` (flatMap), `?` on `Option` in an `Option`-returning fn.
- `if let Some(x) = opt { }`; `let Some(x) = opt else { return; };` (let-else, early exit binding into outer scope).

## Errors
- Libraries: `thiserror` — one enum per crate, `#[error("...")]` messages, `#[from]` for auto-conversion. Callers can match variants.
- Applications: `anyhow::Result<T>` + `.context("reading config")` to add breadcrumbs; `bail!`/`anyhow!` to construct. Don't expose `anyhow` in a library's public API.

## Traits / generics / trait objects
- `#[derive(Debug, Clone, PartialEq, Eq, Hash, Default)]` where applicable. `impl Trait for Type`. Provide default methods in the trait.
- **Static dispatch** (generics/`impl Trait`): monomorphized, zero-cost, larger binary. Accept `fn f(x: impl Display)` or `fn f<T: Display>(x: T)`.
- **Dynamic dispatch** (trait objects): `Box<dyn Trait>` / `&dyn Trait` — one type erased behind a vtable, runtime cost, needed for heterogeneous collections `Vec<Box<dyn Draw>>`. Trait must be object-safe (no generic methods, no `Self` returns).
- Return `impl Iterator` for lazy chains; `Box<dyn Iterator>` when the concrete type varies. Bounds: `where T: Clone + Send`.

## Iterators / closures (lazy until consumed)
```rust
let v: Vec<i32> = xs.iter().filter(|&&n| n > 0).map(|&n| n * 2).collect();
```
- Nothing runs until a consumer: `collect`, `sum`, `for`, `count`, `fold`, `find`, `any`. Prefer chains over index loops.
- `iter()` yields `&T`, `iter_mut()` yields `&mut T`, `into_iter()` yields `T` (consumes). `enumerate`, `zip`, `flat_map`, `take_while`, `chunks`, `windows`.
- Closures: `Fn` (borrows), `FnMut` (mutates capture), `FnOnce` (consumes). `move ||` forces capture by value — needed for threads/`'static`.

## Pattern matching / enums
```rust
match x {
    0 => a,
    1..=9 => b,
    Msg::Move { x, y } => ...,
    Some(n) if n > 0 => ...,     // guard
    _ => c,                       // exhaustive: must cover all
}
let Point { x, y } = p;           // irrefutable destructure
```
- Enums carry data per variant; `Option`/`Result` are enums. `matches!(x, Pat)` for a bool test.

## Smart pointers
- `Box<T>` heap alloc / recursive types / trait objects. `Rc<T>` shared ownership single-thread (refcount, non-atomic). `Arc<T>` shared across threads (atomic refcount). `RefCell<T>` interior mutability with **runtime** borrow check (panics on violation). Combine: `Rc<RefCell<T>>` (shared mutable, single-thread), `Arc<Mutex<T>>` (shared mutable, cross-thread).
- `Cow<'a, T>` clone-on-write: borrow until mutation needed.

## Send / Sync + fearless concurrency
- `Send` = safe to move to another thread; `Sync` = `&T` safe to share across threads. Auto-derived; `Rc`/`RefCell` are neither → won't compile across threads (that's the safety net).
- `std::thread::spawn(move || ...)` needs `'static` + `Send` captures. Share state via `Arc<Mutex<T>>`; message-pass via `std::sync::mpsc` channels. `thread::scope` (1.63+) allows borrowing non-`'static` locals.

## async (tokio)
- `async fn` returns a `Future` (lazy — does nothing until polled/awaited). `.await` yields to the runtime. Need an executor: `#[tokio::main] async fn main()`.
- Concurrency: `tokio::join!(a, b)` (both), `tokio::select!` (first ready + cancel branches), `tokio::spawn(fut)` (needs `Send + 'static`). `tokio::time::timeout(dur, fut)`.
- Never block the runtime: no `std::thread::sleep`, no heavy CPU in a task — use `tokio::time::sleep` and `spawn_blocking` for blocking work.

## Cargo / modules
- `mod foo;` declares (looks for `foo.rs` / `foo/mod.rs`), `use crate::foo::Bar;` imports, `pub`/`pub(crate)` control visibility. Items are private by default. `cargo clippy` and `cargo fmt` always; `cargo build --release` for optimized; `cargo test`, `cargo bench`. `[features]` gate optional deps; workspaces share a lockfile across crates.
- `String` owned/growable vs `&str` borrowed view — take `&str` in args (accepts both). `&[T]` slice over `&Vec<T>`. `Vec::with_capacity(n)` when size known to avoid reallocs. `Vec<u8>`/`&[u8]` for bytes; `.to_owned()`/`String::from` to own a `&str`.

## Common conversions / idioms
- `From`/`Into` for infallible conversion (`String::from(s)`, `x.into()`); `TryFrom`/`TryInto` for fallible (returns `Result`). Implement `From`, get `Into` free.
- `Default::default()` for zero-value construction; `#[derive(Default)]`. Builder pattern for many optional fields.
- `impl Display` for user-facing text (enables `.to_string()`); `Debug` (`{:?}`, `{:#?}` pretty) for devs. Newtype `struct Meters(f64)` to add type safety over primitives.
- Shadowing `let x = x.trim();` rebinds (can change type) — idiomatic, not mutation. Prefer `if let`/`match` over `.unwrap()` at boundaries.

## Gotchas → fix
- **Move-after-use / partial move**: value moved into a call then used again → borrow (`&`) or `clone()` deliberately, or restructure. Moving one field out of a struct partially moves it.
- **Borrow-checker fight (mutable + immutable)**: can't hold `&x` and `&mut x` together → shorten the immutable borrow's scope, copy the needed value out first, or use indices instead of refs.
- **Integer overflow** panics in debug, wraps in release → use `checked_add` (`Option`), `saturating_add`, or `wrapping_add` explicitly.
- **Rc reference cycles** leak (refcount never hits 0) → break with `Weak<T>` for back-pointers; `weak.upgrade()` to access.
- **`RefCell` double-borrow** panics at runtime, not compile time → keep borrow scopes tiny, don't hold a `borrow_mut()` across a call that re-borrows.
- **Iterator invalidation avoided**: you can't push to a `Vec` while iterating `&`— compiler stops you; collect indices/new vec instead.
- **`unwrap()` in prod** turns recoverable errors into crashes → `?` + typed errors.
- **`clone()` reflex** hides design smells and costs allocations → prefer borrows; clone only when ownership is genuinely needed.
- **Blocking in async** stalls all tasks on that worker → `spawn_blocking`.
- **Comparing floats / `derive(Eq)` on `f64`** won't compile (`f64: !Eq`) — only `PartialEq`/`PartialOrd`; sort floats with `.sort_by(|a,b| a.partial_cmp(b).unwrap())` or `.total_cmp`.
- **String indexing `s[0]`** doesn't compile (UTF-8 is variable-width) → `s.chars().nth(0)`, `s.bytes()`, or slice on known byte boundaries `&s[0..4]` (panics mid-char).
- **Returning a reference to a local** → won't compile (dangling); return the owned value or take a buffer. Use-after-move on a `Copy` type is fine (it copies), on non-`Copy` it errors.
- **Holding a `MutexGuard` across `.await`** can deadlock/blocks — drop the guard before awaiting, or use `tokio::sync::Mutex`.

## Testing / docs
- `#[cfg(test)] mod tests` + `#[test] fn ...`; `assert_eq!`, `assert!`, `#[should_panic]`. `cargo test`. Doc tests run code in `///` doc comments. `?` works in tests returning `Result<(), E>`.
