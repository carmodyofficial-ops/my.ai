# Modern C++ & C Idioms

## RAII — own resources via lifetime
Every resource (memory, file, lock, socket) lives in an object; destructor frees it. No manual cleanup paths.
```cpp
std::lock_guard<std::mutex> lk(m);  // unlocks on scope exit
std::ofstream f("x");               // closes automatically
```

## Smart pointers — never raw new/delete
- `unique_ptr<T>` by default; one owner, zero overhead.
- `shared_ptr<T>` only for genuine shared ownership; `weak_ptr` breaks cycles.
```cpp
auto p = std::make_unique<Foo>(args);
auto s = std::make_shared<Bar>();
```
Pass non-owning views as `T&`/`const T&`/`T*`, not smart-pointer copies.

## Move semantics
Transfer instead of copy: `auto b = std::move(a);` — `a` is now empty-but-valid. Take sinks by value, `std::move` into members. Don't use a moved-from object except to reassign/destroy.

## STL containers + algorithms
`vector` default; `unordered_map` for hashing, `map` for ordered. Prefer algorithms over loops:
```cpp
std::sort(v.begin(), v.end());
auto it = std::find(v.begin(), v.end(), x);
std::transform(v.begin(), v.end(), out.begin(), f);
```

## Idioms
- `auto` for obvious/long types; range-for: `for (const auto& e : v)`.
- `const`-correct everything; references over pointers when non-null.
- `nullptr` not `NULL/0`; `enum class Color { Red };` not bare enum.

## C — manual memory
```c
T* p = malloc(n * sizeof *p);   // sizeof the deref, not type
if (!p) return -1;              // always null-check
free(p); p = NULL;              // pair + clear to avoid double-free
```

## Gotchas (UB / bugs)
- Use-after-free / dangling: don't return refs/ptrs to locals or freed memory.
- Double-free: null after free; single owner.
- Uninitialized memory: always init; reading it is UB.
- Buffer overflow / OOB index: check bounds; `.at()` to trap.
- Signed overflow is UB; use unsigned/checked math.
- Leaks: every malloc one free; let RAII own in C++.
- Dangling reference: `const auto& r = temp();` past lifetime.
