# Elixir Idioms

## Pattern matching (the central idea)
- `=` is *match*, not assign: `{:ok, val} = do_thing()` binds `val` or raises `MatchError`. Destructures maps, tuples, lists, structs, binaries.
- Match in function heads — multiple clauses, first match wins:
```elixir
def handle({:ok, v}), do: v
def handle({:error, r}), do: raise r
def area(%Circle{r: r}), do: 3.14 * r * r
```
- List `[head | tail]`, cons to prepend `[x | list]`. `_` ignores; `_name` binds-but-unused. Pin `^x` matches existing value instead of rebinding.
- Guards: `def f(n) when is_integer(n) and n > 0`. Limited set of allowed guard functions (`is_*`, comparisons, `in`, arithmetic — no arbitrary calls).
- `with` chains matches, short-circuits on first non-match: `with {:ok, a} <- fa(), {:ok, b} <- fb(a), do: {:ok, a+b}` — `else` handles the failing pattern.
- `case`, `cond` (first truthy), `if`/`unless` (only nil/false are falsy).

## Immutability & data
- All data immutable; "updating" returns a new copy. Maps `%{k: v}`, update `%{map | k: v2}` (key must exist) or `Map.put`. Access `map[:k]` (nil if missing) or `map.k` (raises if missing).
- Structs are tagged maps with defined keys: `defstruct [:name, age: 0]`; `%User{name: "x"}`. Compile-time key checks.
- Keyword lists `[a: 1, b: 2]` (ordered, dup keys allowed) for options; the last function arg convention. Strings are UTF-8 binaries; charlists `~c"abc"` are lists of codepoints (different!).
- No mutable state in-process — state lives in processes (see OTP).

## Pipe operator
- `|>` passes left result as **first arg** of right: `data |> Enum.map(&f/1) |> Enum.filter(&g/1) |> Enum.sum()`. Design APIs so the "subject" (collection/struct) is arg 1.
- `&` capture: `&(&1 + 1)` anon fn, `&Mod.fun/2` named capture. Enum is eager; `Stream` is lazy (composes without intermediate lists) — `Stream.map |> Enum.take(5)`.

## Processes, OTP, "let it crash"
- Processes are lightweight (not OS threads), isolated heaps, communicate only by message passing. `spawn`, `send(pid, msg)`, `receive do pattern -> ... end`. Millions run concurrently on the BEAM scheduler.
- **GenServer** = stateful server process. Callbacks: `init/1` (returns `{:ok, state}`), `handle_call/3` (sync, replies), `handle_cast/2` (async, no reply), `handle_info/2` (raw messages). Client API wraps `GenServer.call(pid, req)` / `GenServer.cast`.
```elixir
def handle_call(:pop, _from, [h | t]), do: {:reply, h, t}
def handle_cast({:push, x}, stack), do: {:noreply, [x | stack]}
```
- **Supervisor** restarts crashed children per strategy: `:one_for_one` (restart just it), `:one_for_all`, `:rest_for_one`. Child specs + restart intensity limits.
- **"Let it crash"**: don't defensively rescue; let a process die on bad state and let its supervisor restart it to a known-good state. Isolation means one crash doesn't corrupt others.
- `Task.async/await` for parallel work; `Task.Supervisor`; `Agent` for simple shared state; `Registry` for named process lookup. `:ets` for shared in-memory tables.
- Links (`spawn_link`) propagate crashes; monitors (`Process.monitor`) send `:DOWN` messages without dying.

## Ecto (DB)
- Schema maps table: `schema "users" do field :name, :string; has_many :posts, Post end`.
- Changesets validate + cast: `cast(user, attrs, [:name]) |> validate_required([:name]) |> unique_constraint(:email)`.
- Query DSL: `from u in User, where: u.active == true, order_by: u.name, preload: [:posts]`. `Repo.all`, `Repo.get`, `Repo.insert(changeset)`, `Repo.transaction`. `Repo.preload` to avoid N+1.

## Phoenix + LiveView
- Router → controller → view/template, or LiveView. Contexts group domain logic (bounded modules over schemas).
- **LiveView**: server-rendered, stateful over WebSocket; no custom JS for interactivity. `mount/3` sets initial `assigns`, `handle_event/3` responds to UI events (`phx-click`), `handle_info/2` for pubsub. Re-renders diff sent to client. `assign(socket, :count, n)`, `~H"""..."""` HEEx templates. `Phoenix.PubSub` for broadcast.

## Protocols & behaviours
- **Protocol** = polymorphism by data type (like typeclasses/interfaces on data): `defprotocol Size do def size(x) end` + `defimpl Size, for: List`. `Enumerable`, `String.Chars` (`to_string`), `Inspect` are protocols.
- **Behaviour** = a contract of callbacks a module must implement: `@callback handle(x :: term) :: :ok`. `@impl true` on implementations. GenServer/Supervisor are behaviours.

## Modules, functions, tooling
- `defmodule M do def f(x), do: ... end`. Private `defp`. Default args `def f(x, opts \\ [])`. Multiple clauses dispatch by pattern/guard. Module attributes `@moduledoc`, `@doc`, `@type`, compile-time constants `@pi 3.14`.
- Mix build tool: `mix new app`, `mix deps.get`, `mix test`, `mix compile`, `mix run`, `iex -S mix` (REPL with project). Deps in `mix.exs`. Hex is the package registry.
- Testing: ExUnit — `test "adds" do assert add(1,2) == 3 end`; `assert`/`refute`, `assert_raise`, doctests from `@doc` examples.
- `Enum`/`Map`/`String`/`Keyword`/`List` stdlib modules. `IO.inspect(x, label: "debug")` returns `x` (pipe-friendly debugging). `Kernel` functions imported by default.

## Typespecs & structs
- `@spec add(integer, integer) :: integer` documents + enables Dialyzer static analysis. `@type user :: %User{}`.
- Comprehensions: `for x <- 1..10, rem(x,2)==0, do: x*x` (filter + map); `for {k, v} <- map, into: %{}, do: {k, v*2}`. Multiple generators = nested loop.

## Gotchas -> Fix
- Rebinding vs mutation: `x = 1; f(); x` — `x` unchanged; functions can't mutate caller vars. Return new values and rebind.
- `map.key` raises `KeyError` on missing key; `map[:key]` returns nil. Pick based on whether missing is a bug.
- `%{map | :k => v}` **requires** key to exist (raises otherwise) — use `Map.put` to add.
- Atoms are never garbage collected — never `String.to_atom(user_input)` (memory exhaustion / DoS); use `String.to_existing_atom/1`.
- `Enum` builds full intermediate lists — for large/infinite data or pipelines, use `Stream` then a terminal `Enum`.
- Charlist vs string surprise: `IO.inspect ~c"abc"` prints as list; `'abc'` (single quotes) is a charlist not a string. Use `"..."`.
- `receive` with no matching clause blocks forever (mailbox grows) — add a catch-all or `after` timeout.
- GenServer `handle_call` that does slow work blocks that process's mailbox (serial) — offload to Task or reply then continue.
- `++` (list concat) is O(n) on the left list — prepend `[x | list]` (O(1)) and reverse at end, or use appropriate structure.
- Struct update `%User{u | :x => 1}` won't add unknown keys (compile error) — that's a feature; typo protection.
- `with` `else` catches ALL non-matching clauses — pattern-match the specific error shapes or you'll swallow unexpected ones.
- Pipe into a function whose subject isn't arg 1 -> wrap: `x |> then(&SomeMod.fun(other, &1))`.
- Integer `/` always returns float (`4 / 2 == 2.0`); use `div/2` and `rem/2` for integer math.
- Comparing different types never errors (total ordering across types) — `1 < :atom` is valid but meaningless; guard your comparisons.
