# Julia

Dynamic, JIT-compiled (LLVM) technical-computing language. Solves the "two-language problem": high-level like Python, fast like C when code is type-stable. REPL-centric; `]` enters Pkg mode, `?` help, `;` shell.

## Basics
- REPL modes: julian, `]` Pkg, `?` help, `;` shell, `\` LaTeX-completion (`\alpha`+Tab -> α — unicode identifiers allowed). Run scripts `julia file.jl`. `include("f.jl")` splices a file.
- `println`, `@show x`, `print`, string interpolation `"$x and $(a+b)"`. Comments `#`, block `#= =#`. `;` suppresses REPL output.

## Multiple dispatch (the core paradigm)
- Functions have many **methods**; the concrete types of **all** arguments select which runs (not just the first, unlike OOP single dispatch).
```julia
area(c::Circle) = π*c.r^2
area(r::Rect)   = r.w*r.h
```
- `methods(f)` lists them; `@which f(x)` shows which is chosen. Extend others' functions on your types — this is how the ecosystem composes (define `Base.length`, `Base.+`, etc.).
- No classes/methods-on-objects; behavior lives in generic functions, data in `struct`s.

## Type system
- Nominal, hierarchical: abstract types (`abstract type Number end`) organize; concrete types (`struct`) hold data and are leaves (can't subtype a concrete type).
- `struct` immutable by default; `mutable struct` for fields you reassign. Annotate fields with concrete types for speed.
- **Parametric types**: `struct Point{T<:Real}; x::T; y::T; end`; `Vector{Float64}` = `Array{Float64,1}`. Type params enable specialization.
- `::T` annotations are for dispatch/clarity, not required for speed inside functions (inference handles locals).
- `Union{Int,Nothing}`, `Any` (avoid in hot paths).

## Performance
- **Type stability** is the #1 rule: a function's return type must be inferable from arg types; a variable shouldn't change type. Check with `@code_warntype f(x)` — red/`Any`/`Union` = instability.
- **Avoid non-const globals** in hot code: their type can change, so the compiler can't specialize. Mark `const`, or pass as arguments, or wrap work in a function.
- Put real work inside functions (top-level/global scope isn't optimized).
- `@time`/`@btime` (BenchmarkTools) to measure; watch allocations (allocation in a loop = a smell).
- Preallocate outputs; mutate with `!` functions (`push!`, `mul!`). `@views` avoids array-slice copies (slices copy by default!).
- `@inbounds` skips bounds checks (only when certain); `@simd`.

## Broadcasting (dot syntax)
- `f.(x)` applies `f` elementwise; `.+ .* .^` are elementwise operators. Dots **fuse**: `y .= a.*x .+ b` is one loop, zero temporaries.
- `@.` macro dots a whole expression: `@. y = a*x + b`.

## Arrays
- **1-indexed** and **column-major** (like Fortran/MATLAB): iterate inner (first) index fastest for cache locality — `for j in cols, i in rows`.
- `A[i,j]`, `end` = last, `A[:, 1]` column, `A[2:end]`. `1:10` is a lazy range. `zeros(3,3)`, `reshape`, `vcat`/`hcat`.
- Assignment `B = A` aliases; `copy(A)` for a copy.

## Packages & environments
- Stdlib `Pkg`: `] add DataFrames`, `] activate .`, `] instantiate`. `Project.toml` + `Manifest.toml` (reproducible env — commit both). Each project has its own environment.

## Metaprogramming
- Code is data: `:(a + b)` is an `Expr`; `quote ... end`. **Macros** (`@macro`) transform code before eval: receive/return expressions. `@show`, `@assert`, `@time`, `@. ` are macros. `eval` runs an Expr. Use macros sparingly.

## Interop
- **PyCall**/**PythonCall** call Python (`np = pyimport("numpy")`); **JuliaCall** the reverse. `ccall((:func,"lib"), RetT, (ArgTs...,), args...)` for C — zero-overhead, no wrapper. `@cfunction` passes Julia funcs to C. `RCall` for R.

## Functions & control
- `f(x) = x^2` one-liner; `function f(x) ... end` block; anonymous `x -> x^2`. Return is last expr (or explicit `return`). Optional args `f(x, y=1)`, keyword args after `;`: `f(x; scale=1)`. Splat `f(args...)`; slurp `f(args...)`.
- Type-based method specialization is automatic; `where` clause: `f(x::T) where {T<:Number}`.
- `do` block passes a closure as first arg: `open("f") do io ... end`, `map(x) do v ... end`.
- `1:10` range, `collect` to materialize, comprehensions `[x^2 for x in 1:5 if isodd(x)]`, generators `(x^2 for x in it)`. Ternary `c ? a : b`, `&&`/`||` short-circuit (also used as guards).

## Types, conversion, missing data
- `Int`, `Float64`, `Bool`, `Char`, `String` (UTF-8, immutable, indexed by byte — use `eachindex`/`nextind`), `Symbol` (`:sym`), `Rational` (`3//4`), `Complex` (`2im`), `BigInt`/`BigFloat`.
- `missing` (propagates: `1 + missing === missing`; `skipmissing`), `nothing` (absence, `Union{T,Nothing}`), `NaN`. `isnothing`, `coalesce`. `Some(x)` wraps.
- `convert(T, x)`, `T(x)`, `parse(Int, "5")`, `string(x)`. `promote` unifies numeric types.

## Errors & tooling
- `try ... catch e ... finally ... end`; `throw(ArgumentError("..."))`, `error("msg")`, `@assert cond`. `Base.@kwdef` for keyword-constructor structs.
- Testing: stdlib `Test` (`@test`, `@testset`, `@test_throws`). Profiling: `@profile`, `Profile.print`, `@allocated`, `@code_native`/`@code_llvm`. Revise.jl for live code reload. Debugger.jl / Infiltrator.jl.

## Gotchas -> Fix
- **Type instability tanks speed** (10–100x): a variable that changes type or an inferred `Any` return -> restructure, use `@code_warntype`, annotate return, avoid `x = 0` then `x = 1.5`.
- **Global scope is slow**: benchmarking in REPL top-level misleads and allocates -> wrap in a function or use `const` / `$` interpolation in `@btime`.
- **1-indexing** trips Python/C users: first element `a[1]`, last `a[end]`, off-by-one in ported code -> use `eachindex(a)`, `firstindex`/`lastindex`, `begin`.
- **Column-major**: row-major iteration order thrashes cache -> loop columns outer, rows inner.
- **Array slices copy**: `A[:,1]` allocates -> use `@view`/`@views` to avoid.
- **World-age error** ("method too new"): calling a function/`eval`'d method defined after the calling function was compiled, inside the same call -> call from top level, use `Base.invokelatest`, or restructure; common with `eval` in loops.
- **`Vector{Any}`** from untyped literals or growing an unannotated array -> give containers concrete element types.
- **Broadcasting shape mismatch** or forgetting `.` on one op breaks fusion -> use `@.`.
- **Mutable default / aliasing**: `b = a; b[1]=0` mutates `a` -> `copy`.
- **Integer overflow is silent**: `2^63` wraps (`Int64`) -> use `big"..."`/`BigInt` or `Int128` when needed; `factorial(21)` overflows.
- **`==` vs `===`**: `==` value equality (float tolerance issues), `===` identity. `1 == 1.0` true, `1 === 1.0` false.
- **First-call latency ("time to first plot")**: JIT compiles on first use -> expected; use PrecompileTools / sysimages; don't confuse with runtime speed.
- **`function` vs one-liner scope**; `for`/`let` introduce new scope — assigning a global inside a loop errors or needs `global` (REPL top-level is lenient, scripts stricter).
- **Abstractly-typed struct fields** (`x::Real` / `x::AbstractArray` / untyped) box values and defeat specialization -> use concrete or parametric (`x::T where T<:Real`) fields in performance structs.
- **Type piracy**: defining a method on types you don't own (both function and all arg types from elsewhere) can silently break other packages -> only extend when you own the function or a type.
- **`@simd`/`@inbounds` on wrong loop** produces wrong results or crashes if bounds actually violated -> use only when provably safe.
- **String indexing is by byte**, so `s[2]` on a multibyte char errors -> iterate with `for c in s` or use `eachindex`/`nextind`.
- **`missing` propagation**: comparisons/arith with `missing` yield `missing` (not `false`), so `if x == 1` errors when `x` is missing -> use `isequal`, `coalesce`, `skipmissing`.
- **Mutating a function arg** (Julia is pass-by-sharing): `push!` on a passed array mutates the caller's -> `copy` if you must not; name mutating fns with `!`.
