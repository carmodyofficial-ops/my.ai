# Rust Idioms

## Ownership
- One owner; move on assign/pass. `let b = a;` invalidates `a` (non-Copy).
- `&T` shared (many), `&mut T` exclusive (one). Never both at once.
- `clone()` is explicit and visible—if you're cloning to dodge the borrow checker, restructure (narrow scopes, split borrows, pass refs) instead.

## Result/Option
- `?` propagates `Err`/`None` early: `let f = File::open(p)?;`.
- No `unwrap()` in production. Use `?`, or `.expect("invariant: …")` when truly impossible.
- `opt.map(..).unwrap_or(d)`, `ok_or(e)?`, `if let Some(x) = opt`, `let Some(x) = opt else { return; };`.

## Errors
- Libraries: `thiserror` enum per crate. Apps: `anyhow::Result<T>` + `.context("…")`.

## Match / flow
```rust
match x { 0 => a, 1..=9 => b, _ => c }
while let Some(v) = it.next() { … }
let Point{x,y} = p;            // destructure
```

## Traits
- `#[derive(Debug, Clone, PartialEq)]`. `impl Trait for Type`.
- Accept `impl Trait`/generics; return `impl Iterator` for lazy chains.

## Iterators (lazy until collected)
```rust
let v: Vec<i32> = xs.iter().filter(|&&n| n>0).map(|&n| n*2).collect();
```
Prefer iterator chains over index loops.

## Strings & slices
- `String` owned/growable; `&str` borrowed view. Take `&str` in fn args.
- `&[T]` slice over `&Vec<T>`. `Vec::with_capacity` when size known.

## Smart pointers
- `Box<T>` heap/recursive. `Rc<T>` shared single-thread. `Arc<T>` shared across threads. `RefCell<T>` interior mut (runtime borrow check). Combine: `Rc<RefCell<T>>`, `Arc<Mutex<T>>`.

## Lifetimes
- Usually elided. Annotate only when tying outputs to inputs: `fn first<'a>(s:&'a str)->&'a str`.

## Cargo / modules
- `mod foo;` + `use crate::foo::Bar;`. `pub` to export. `cargo clippy` always.

## Gotchas
- Move-after-use: borrow (`&`) or `clone()` deliberately.
- Integer overflow panics in debug; use `checked_/wrapping_/saturating_add`.
- Don't `.clone()` reflexively—it hides design smells.
