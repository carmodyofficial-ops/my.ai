# Lua Scripting

Small, fast, embeddable scripting language. One data structure (`table`), one number type historically, prototype-based OOP. Ubiquitous as an embedded/config/game-scripting language (Redis, Nginx/OpenResty, Neovim, game engines). **1-indexed.**

## Values & types
- 8 types: `nil`, `boolean`, `number`, `string`, `table`, `function`, `userdata`, `thread`.
- Only `nil` and `false` are falsy; **`0` and `""` are truthy**.
- `and`/`or` short-circuit and return operands: `x = a or default`, `y = cond and t or f` (ternary idiom — fails if `t` is falsy).
- Strings immutable; `..` concatenates; `#s` length; `\n` etc.

## Tables — the universal structure
- Arrays, dicts, objects, namespaces — all tables. `t = {}`; `t.k = 1` == `t["k"] = 1`; `t[1] = "a"`.
- Array literal `{10,20,30}` indexes from **1**. `#t` = length of the **array (sequence) part** only.
- `ipairs(t)` iterates `1..n` until first `nil` (stops at hole); `pairs(t)` iterates all keys (unordered).
- `table.insert`, `table.remove`, `table.concat`, `table.sort`. Any value except `nil`/`NaN` can be a key.

## Metatables & metamethods
- Attach behavior with `setmetatable(t, mt)`; `getmetatable`. Metamethods are keys with `__`:
- `__index`: called on missing-key read — a table (delegate/fallback) or function. Basis of OOP & inheritance.
- `__newindex`: intercept writes to absent keys. `__call`: make table callable. Arithmetic `__add __sub __mul __eq __lt __le`, `__tostring`, `__len`, `__concat`, `__gc`.
```lua
local V = {}
V.__index = V
function V.new(x) return setmetatable({x=x}, V) end
function V:get() return self.x end   -- : adds implicit self
local v = V.new(5); print(v:get())   -- 5
```

## OOP via metatables
- Class = table; instances get `setmetatable(obj, Class)` with `Class.__index = Class`. Method call `obj:m(a)` == `obj.m(obj, a)` (colon passes `self`). Inheritance: chain `__index` to parent, or `setmetatable(Sub, {__index = Base})`.

## Closures & scoping
- **`local` or it's global!** Bare assignment creates/uses a global. Always `local x = ...`.
- Lexical scope; functions capture **upvalues** by reference. Closures are the idiom for state/private data and callbacks.
- `local function f()` for recursion (declares name before body).

## Coroutines
- Cooperative, single-threaded. `coroutine.create(fn)` -> `coroutine.resume(co, ...)`; inside, `coroutine.yield(...)` suspends and returns values to resumer; next `resume` continues. `coroutine.wrap` returns a callable. Used for iterators, generators, async-style flow. Not OS threads (no parallelism).

## Error handling
- `error(msg [,level])` raises; `assert(v, msg)` errors if falsy. **`pcall(f, args...)`** -> `ok, result_or_err`; `xpcall(f, handler)` adds a traceback handler. Errors can be any value, not just strings.

## String patterns (NOT regex)
- Lua patterns: `%a` alpha, `%d` digit, `%s` space, `%w` alnum, `%p` punct (uppercase = complement `%D`). Magic chars `( ) . % + - * ? [ ] ^ $`; **`%` escapes** (not `\`). No alternation `|`, no `{n,m}` — quantifiers are `* + - ?` only (`-` = lazy).
- `string.match`, `:gmatch` (iterator), `:gsub` (replace, returns count), `:find`. Captures with `()`.

## Embedding / C API
- Stack-based C API: `lua_State*`, `luaL_newstate`, push/pop (`lua_pushnumber`, `lua_tostring`), `lua_pcall`. Register C funcs (`lua_CFunction`, return # of results). `luaL_openlibs`. Host controls sandboxing (remove `os`, `io`). `require` loads modules (a chunk returning a table).

## LuaJIT
- Tracing JIT, near-C speed; targets Lua **5.1** semantics (+ some extras). Adds **FFI** (`ffi.cdef`/`ffi.C`) to call C without the stack API. Not all newer 5.x features. Widely used where speed matters (OpenResty, games).

## Functions, varargs, multiple returns
- Functions are first-class values; `local f = function() end` or `local function f() end`. Multiple returns: `return a, b`; capture `local x, y = f()`. `...` = varargs; `select('#', ...)` counts, `{...}` packs (holes if `nil`s), `table.pack`/`table.unpack` (5.2+).
- Multiple-return adjustment: only the **last** expression in a list expands; `f(), g()` -> `g` truncated to 1 value; wrap in `()` to force one value. `a = {f()}` collects all.

## Standard library essentials
- `string` (`.format`, `.rep`, `.sub`, `.upper/.lower`, `.byte/.char`, patterns), `table`, `math` (`.floor`, `.random`, `.huge`, `.maxinteger`), `os` (`.time`, `.date`, `.clock`, `.getenv` — often sandboxed out), `io` (files), `require`/`package.path`, `tostring`/`tonumber`, `type`, `rawget`/`rawset`/`rawequal`/`rawlen` (bypass metamethods).
- `_G` = global environment table. `#` length, `..` concat, `%` modulo, `^` power (always float), `//` floor div (5.3+).

## Modules
- A module is a chunk returning a table: `local M = {}; function M.f() end; return M`, loaded via `local m = require("mymod")`. `package.loaded` caches (loaded once). Avoid setting globals from modules.

## Garbage collection
- Automatic (incremental mark-sweep; 5.4 adds generational). `collectgarbage("collect"|"count"|"step")`. **Weak tables** via `__mode = "k"|"v"|"kv"` metafield allow keys/values to be collected (caches). `__gc` finalizer on tables (5.2+) / userdata.

## Versions
- 5.1 → 5.2 (`_ENV`, `goto`, `table.pack/unpack`) → 5.3 (**integer subtype**, bitwise `& | ~ >> <<`, `//`, UTF-8 lib) → 5.4 (`<close>` to-be-closed vars, `<const>`, generational GC). Note `goto`+labels `::label::` exist (5.2+) for loop breaks. LuaJIT tracks 5.1.

## Gotchas -> Fix
- **Accidental globals**: forgetting `local` pollutes global namespace, causes spooky bugs -> always `local`; lint with `luacheck`; set a metatable on `_G` with `__newindex` to trap stray globals in dev.
- **1-indexing**: loops/arrays start at 1; `t[0]` is not in the sequence -> use `1..#t`, `ipairs`.
- **`nil` holes break arrays**: `#t` and `ipairs` stop at the first `nil`, giving wrong length -> don't leave gaps; use `table.remove` (shifts) not `t[i]=nil`; track your own count.
- **`#t` on a table with holes is undefined** (any border) -> keep sequences dense.
- **`ipairs` vs `pairs`**: `ipairs` misses non-integer/holey keys; `pairs` order is unspecified -> pick deliberately.
- **`a and b or c` ternary fails when `b` is `false`/`nil`** -> use `if` or ensure `b` truthy.
- **Integer vs float (5.3+)**: `3/2 == 1.5` (float), `//` for floor; `2^2` is a float `4.0`; table keys `1` and `1.0` collide/differ subtly -> use `//`, `math.type`, `math.tointeger`.
- **Unhandled error kills the coroutine/host**: wrap risky calls in `pcall`; check the `ok` flag.
- **String patterns aren't regex**: `.` `%` `-` behave differently, no `|`/`\d` -> use `%d`, escape magic chars with `%`.
- **Comparing different types** (`1 == "1"`) is always `false`, no coercion in `==` (but arithmetic coerces numeric strings) -> convert explicitly (`tonumber`).
- **1-based `string.sub`/negative indices** count from end (`s:sub(-3)`).
- **Numbers are doubles by default** (pre-5.3): large integers lose precision beyond 2^53.
