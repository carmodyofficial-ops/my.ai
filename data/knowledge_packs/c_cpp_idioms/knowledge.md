# Modern C++ & C Idioms

## RAII — own every resource by lifetime
Memory, files, locks, sockets live in an object; destructor releases. No manual cleanup paths, exception-safe by construction.
```cpp
std::lock_guard lk(m);        // unlocks on scope exit (CTAD, no <mutex> args)
std::ofstream f("x");         // closes automatically
std::unique_ptr<FILE,decltype(&fclose)> h(fopen(p,"r"),&fclose);
```
Never write a bare `new`/`delete`, `fopen` without an owner, or `lock`/`unlock` pairs.

## Smart pointers
- `unique_ptr<T>` **default** — one owner, zero overhead, move-only. `make_unique<T>(args)`.
- `shared_ptr<T>` only for genuine shared ownership — atomic refcount cost. `make_shared` (one allocation, but keeps control block alive as long as any `weak_ptr`).
- `weak_ptr<T>` breaks reference cycles; `.lock()` to use (returns `shared_ptr` or null).
- Pass **non-owning views** as `const T&`/`T&`/`T*`/`std::span<T>`, never `shared_ptr` by value (bumps refcount). Take a `shared_ptr` by value only when you store it.

## Move semantics & rule of 0/5
- `auto b = std::move(a);` transfers; `a` is valid-but-unspecified — only reassign/destroy it.
- **Rule of 0**: own resources via members that already manage themselves (`vector`, `unique_ptr`) → write no special members. Prefer this.
- **Rule of 5**: if you write one of {dtor, copy ctor, copy assign, move ctor, move assign}, consider all five. Declaring a dtor/copy suppresses implicit moves.
- Sink params by value + `std::move` into member: `void set(std::string s){ s_=std::move(s); }`.
- `noexcept` move ctor lets `vector` move (not copy) on reallocation.

## const-correctness & references
- `const` everything that doesn't mutate: member fns, params, locals. `const T&` params avoid copies.
- References for non-null, no-rebind; pointers for optional/rebindable (`std::optional<T&>` doesn't exist — use `T*`).
- `constexpr` for compile-time constants/functions; `consteval` forces compile-time; `if constexpr` prunes template branches.
- `nullptr` not `NULL`/`0`; `enum class Color{Red}` not bare enum (scoped, no implicit int).

## STL containers & algorithms
`vector` by default; `unordered_map`/`unordered_set` for hashing, `map`/`set` for ordered; `deque` for both-ends; `array<T,N>` fixed. Reserve when size known: `v.reserve(n)`.
```cpp
std::sort(v.begin(), v.end());
std::erase_if(v, pred);                 // C++20, no erase-remove idiom
auto it = std::find(v.begin(), v.end(), x);
std::ranges::sort(v);                   // ranges: pass the container
auto evens = v | std::views::filter(f) | std::views::transform(g);
```
`emplace_back` constructs in place; `push_back(std::move(x))` for existing. `at()` bounds-checks (throws), `operator[]` does not.
- Lookup: `map.contains(k)` (C++20); `if (auto it=m.find(k); it!=m.end())`; `m[k]` **inserts** a default if absent (surprise mutation of `const`-intent code) — use `find`/`at`/`contains`.
- Iterate without copy: `for (const auto& [k,v] : m)`. Sorted `map`/`set` are trees (log n); `unordered_*` are hashes (avg O(1), custom hash for user keys).
- `std::move` a container into a sink; small-string optimization means short `std::string` avoids heap. `shrink_to_fit`, `clear` keeps capacity.

## C — manual memory & UB
```c
T* p = malloc(n * sizeof *p);   // sizeof the deref, not the type name
if (!p) return -1;              // always null-check
free(p); p = NULL;              // pair + clear to block double-free
```
- `sizeof *p` survives type changes; `malloc(n*sizeof(T))` drifts.
- `strncpy` doesn't null-terminate on overflow; prefer `snprintf`.
- Array decays to pointer — `sizeof arr` only works in the defining scope; pass length explicitly.
- `restrict` promises no aliasing (optimization); `volatile` is for memory-mapped I/O, NOT threading (use `<stdatomic.h>`/`std::atomic`). `static inline` in headers.
- Zero-init `T x = {0};` / `calloc`. `memcpy` non-overlapping, `memmove` overlapping. Flexible array member `T arr[];` last in struct.
- Prefer `size_t` for sizes/indices; `<stdint.h>` fixed widths (`int32_t`, `uint64_t`). Undefined: signed overflow, OOB, null deref, data races, strict-aliasing violation, uninitialized read.

## Gotchas -> Fix
- **Use-after-free / dangling ref**: returning `&`/`*` to a local or freed block -> return by value, or ensure lifetime outlives use; `const auto& r = temp();` binds a temporary (lifetime-extended) but `const auto& r = f().member;` does NOT — copy it.
- **Double free**: -> single owner (`unique_ptr`); null the pointer after `free`.
- **Iterator/reference invalidation**: `push_back`/`insert` may reallocate `vector`, invalidating all iterators/pointers/refs; `erase` invalidates from the point on. -> re-acquire iterators; use returned iterator of `erase`; `reserve` up front.
- **Uninitialized read** (UB): -> always initialize (`int x{};`, `= {}`); `-Wall -Wextra`, MSan/`-fsanitize=address,undefined`.
- **Signed integer overflow** (UB): -> use unsigned or checked (`__builtin_add_overflow`, `<stdckdint.h>`); never rely on wrap for signed.
- **Object slicing**: assigning/passing a derived by value to a base drops the derived part -> pass `Base&`/`Base*`; make base non-copyable or abstract.
- **Missing virtual dtor**: `delete base_ptr` to a derived with non-virtual dtor is UB -> `virtual ~Base()=default` on any polymorphic base.
- **Dangling `string_view`/`span`**: viewing a temporary/rvalue -> ensure the backing buffer outlives the view; don't return a `string_view` into a local.
- **RAII violation**: acquiring a resource then early-`return`/throw before manual release -> wrap in a guard object; never manual paired acquire/release.
- **`shared_ptr` cycle**: two objects hold `shared_ptr` to each other -> one side holds `weak_ptr`.
- **`make_shared` + `weak_ptr` memory**: object storage isn't freed until last `weak_ptr` dies (shared control block) -> use `make_unique` or separate alloc for large objects with long-lived weak refs.
- **Copying `shared_ptr` in a hot path**: atomic refcount contention -> pass `const shared_ptr&` or a raw view.
- **Narrowing / implicit conversions**: -> brace-init `{}` diagnoses narrowing; `static_cast` deliberately.
- **`vector<bool>`**: proxy type, not real `bool&` -> use `std::vector<char>`/`std::deque<bool>` if you need refs/addresses.
- **Comparing signed/unsigned**: `-1 < 1u` is false (UB-adjacent surprise) -> `std::cmp_less` (C++20) or keep types consistent; `-Wsign-compare`.
- **Returning `move` of a local**: `return std::move(x);` defeats NRVO -> just `return x;`.
- **Dangling capture in lambda**: `[&]` capturing a local that outlives the scope (stored callback) -> capture by value/`[=]` or move.
- **ODR / static init order fiasco**: cross-TU global depends on another global's init order -> function-local `static` (Meyers singleton), initialized on first use.
- **Memory leak**: every `malloc` needs a `free`; -> let RAII/`unique_ptr` own; run ASan/Valgrind.

## Templates & generic code
- Function/class templates instantiate per type at compile time; put definitions in headers (or explicit instantiation). Errors surface at instantiation, deep and verbose.
- **Concepts** (C++20) constrain and clarify: `template<std::integral T>` / `requires std::sortable<It>` — better errors than SFINAE.
- CTAD deduces class template args: `std::vector v{1,2,3};`, `std::lock_guard lk(m);`.
- `auto`/`decltype(auto)` return deduction; perfect forwarding `template<class T> void f(T&& x){ g(std::forward<T>(x)); }` — `T&&` is a forwarding ref only when `T` is deduced.
- Prefer STL algorithms/ranges over hand loops; prefer `constexpr` computation over runtime + macros. Avoid macros for constants/functions (no scope/type) — `constexpr`/`inline`.

## More idioms
- `std::optional<T>` for maybe-a-value, `std::variant<A,B>` + `std::visit` for a closed sum type, `std::expected<T,E>` (C++23) for error-or-value without exceptions.
- `std::string_view` param for read-only strings (no copy, accepts `char*`/`string`/literal); `std::span<T>` for contiguous ranges.
- Structured bindings: `auto [it, ok] = map.insert(...); auto& [k,v] = *it;`.
- Uniform init `{}` prevents narrowing and the most-vexing-parse (`T t(); ` declares a function). Init members via in-class initializers + delegating ctors.
- `= default`/`= delete` special members explicitly. `override`/`final` on virtual overrides (compiler-checked). `[[nodiscard]]`, `[[maybe_unused]]` attributes.
- Error handling: exceptions for exceptional paths (RAII makes them safe) or `expected`/error codes for expected failures — don't mix half-cleanup.
- Threading: `std::thread`/`std::jthread` (auto-joins, stop token); `std::mutex` + `std::scoped_lock` (multi-lock, deadlock-free order); `std::atomic<T>` for lock-free counters; `std::condition_variable`; `std::async`/`std::future`. A data race is UB — guard shared mutable state.
- `std::format` (C++20) type-safe formatting over `printf`/`iostream`; `<chrono>` for time. Prefer `enum class` + `switch` over magic ints.

## Build — CMake
```cmake
cmake_minimum_required(VERSION 3.20)
project(app CXX)
add_library(core src/a.cpp)
target_include_directories(core PUBLIC include)   # PUBLIC propagates to consumers
target_compile_features(core PUBLIC cxx_std_20)
add_executable(app src/main.cpp)
target_link_libraries(app PRIVATE core)           # PRIVATE = not transitive
```
- Prefer `target_*` (usage requirements) over global `include_directories`/`add_definitions`.
- `PUBLIC`/`INTERFACE`/`PRIVATE` control transitive propagation. `find_package`, `FetchContent`, or a package manager (vcpkg/Conan) for deps.
- Out-of-source build; `CMAKE_BUILD_TYPE=Release` (`-O2 -DNDEBUG`) — `NDEBUG` disables `assert`, so no side effects in `assert`.
- Warnings on: `-Wall -Wextra -Wpedantic` (GCC/Clang), `/W4` (MSVC); treat as errors in CI. Sanitizers: `-fsanitize=address,undefined,thread` in a debug build catch UB/leaks/races early.
- Header vs impl: templates/`inline`/`constexpr` in headers; declare in `.hpp`, define in `.cpp` otherwise; include guards or `#pragma once`. Forward-declare to cut compile dependencies.
