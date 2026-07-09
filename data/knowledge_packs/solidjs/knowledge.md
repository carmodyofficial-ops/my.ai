# SolidJS (fine-grained reactivity, no VDOM)

## Mental model
- **Fine-grained reactivity, no virtual DOM**: JSX compiles (via babel-preset-solid) to real DOM + precise reactive bindings. Only the exact DOM text/attr that depends on a changed signal updates — no diffing, no re-render.
- **Components run ONCE** (at mount) to set up the reactive graph — NOT on every update (unlike React). Function bodies don't re-execute; only tracked expressions in JSX / effects re-run. No `useMemo`/`useCallback`/dependency arrays needed.
- Signals are getter functions: you call them (`count()`), and calling inside a tracking scope subscribes it.

## Signals
- `const [count, setCount] = createSignal(0)` — read `count()`, write `setCount(5)` / `setCount(n => n+1)`. `createSignal(v, {equals:false})` to always notify.
- Reading a signal **inside a tracking scope** (JSX, `createEffect`, `createMemo`) subscribes. Reading outside (component body top-level, event handler) does NOT track — just a value read.
- `createMemo(() => a() * 2)` — cached derived value, itself a signal getter `m()`; recomputes only when deps change; dedupes downstream. Use for expensive/shared derivations.
- `createEffect(() => console.log(count()))` — runs after render + whenever tracked deps change; for side effects (DOM, logging, sync). `on(count, v => ...)` for explicit deps + `{defer:true}`. `createRenderEffect` runs before paint; `onCleanup(fn)` teardown (runs before re-run/dispose).
- `untrack(() => x())` read without subscribing; `batch(() => {...})` group writes into one update; `createRoot(dispose => ...)` for reactive scope outside components.

## Props — DON'T destructure
- Props are a **reactive proxy**; destructuring reads values once at setup and breaks reactivity. Access as `props.name` (live).
- `const [local, others] = splitProps(props, ['name'])` — split while keeping reactivity. `mergeProps(defaults, props)` for defaults (reactive; not `props.x ?? d` at top level).
- Children: `props.children`; use `children(() => props.children)` helper to resolve once when manipulating them.

## Stores (nested/reactive objects)
```ts
const [state, setState] = createStore({ user: { name: 'Ada' }, todos: [] });
state.user.name;                                  // fine-grained read
setState('user', 'name', 'Grace');                // path set
setState('todos', t => [...t, newTodo]);          // functional
setState('todos', i => i.done, 'done', true);     // filter update
setState(produce(s => { s.todos.push(x) }));       // immer-style mutate
setState(reconcile(serverData));                   // diff-merge external data
```
- `createStore` = proxy for nested reactivity; only accessed paths become dependencies (deep fine-grained). Prefer over signals for objects/arrays/lists. `unwrap(state)` for raw.

## Control flow (use components, not JS methods/ternaries in loops)
- `<Show when={user()} fallback={<Login/>}>{u => <p>{u().name}</p>}</Show>` — conditional; callback form narrows non-null.
- `<For each={items()}>{(item, i) => <li>{item.name} {i()}</li>}</For>` — keyed by **reference** (best for dynamic lists; DOM nodes move, not recreate). `<Index each={...}>{(item,i)=>...}</Index>` — keyed by **index** (item is a signal; use when values change but list length/order stable, e.g. inputs).
- `<Switch fallback={...}><Match when={a()}>..</Match></Switch>`, `<Dynamic component={comp()}/>`, `<Portal>`, `<ErrorBoundary fallback={(e,reset)=>...}>`.

## Resources + Suspense (async)
- `const [data] = createResource(sourceSignal, fetcher)` — `data()` value, `data.loading`, `data.error`; refetches when `sourceSignal` changes; `data.latest` keeps prev while refetching. `const [d,{refetch,mutate}] = createResource(...)`.
- Wrap in `<Suspense fallback={<Spinner/>}>` to show fallback while resources load; `<SuspenseList>` orders multiple. Works with SSR streaming in SolidStart.

## Lifecycle
- `onMount(() => {...})` — after first render, client-only (safe for DOM/`window`); no dep tracking. `onCleanup(() => {...})` — on unmount/disposal (also inside effects). No separate update hook — reactivity handles updates.

## Context (DI / shared state)
- `const Ctx = createContext(default); <Ctx.Provider value={store}>{children}</Ctx.Provider>`; consume `const v = useContext(Ctx)`. Provide a store/signal for reactive shared state — avoids prop drilling; scoped to the component subtree. Common pattern: a `makeStore()` factory returning `[state, actions]`.

## Refs, directives, events, JSX
- Refs: `let el; <div ref={el}/>` (assigned before `onMount`) or `ref={r => ...}` callback. Reactive `ref` via `use:` directives: `use:clickOutside` -> compile-time requires the directive imported in scope; signature `(el, accessor) => {}`.
- Events are delegated + native: `onClick={fn}` (synthetic delegation), `on:click` for direct native binding, `onInput`. `classList={{active: isActive()}}` for conditional classes; `style={{color: c()}}`; `attr:`/`prop:`/`bool:` namespaces.
- `<Show keyed when={sig()}>` recreates block when value changes (vs default which keeps block, updates refs). `createUniqueId()` for SSR-safe ids.

## Effects vs memos — when to use
- `createMemo` — derived VALUE consumed in the graph (pure, returns something, cached, no side effects). `createEffect` — SIDE EFFECT reacting to changes (DOM outside JSX, logging, subscriptions; returns nothing). Never set signals from a memo; avoid setting a signal an effect reads without guards.
- `on(deps, cb, {defer})` — explicit dependency list, `defer:true` skips the initial run (like a "watch" that ignores mount). `createComputed` (runs before render, for chained derivations — rare).

## SolidStart (meta-framework)
- File routing `src/routes/`, SSR/SSG/streaming, `"use server"` server functions (RPC), `createAsync` + `query()` for cached data + `cache`/revalidation, `action()` + `useSubmission` for mutations, `<A>`/`useNavigate` from `@solidjs/router`, route `load` preloading. Built on Vinxi/Nitro; deploy via presets.

## Gotchas -> Fix
- Destructuring props (`const {name} = props`) -> reads once, never updates. -> use `props.name` directly, or `splitProps`/`mergeProps`.
- Expecting the component body to re-run on state change -> it runs ONCE. Put anything that must react in JSX, `createMemo`, or `createEffect`; not in the body top-level.
- Reading a signal without calling it (`{count}` instead of `{count()}`) -> passes the getter function, not the value; no reactivity. -> call it: `{count()}`.
- Destructuring/spreading a store loses reactivity -> access by path (`state.user.name`); update by path with `setState(...)`, never mutate the proxy directly outside `produce`.
- `map()`/ternary instead of `<For>`/`<Show>` in JSX -> `array.map()` recreates all DOM on change and doesn't key; conditionals via ternary can over-execute. -> use `<For>` (referential keying) and `<Show>`.
- `<For>` recreates rows when you replace objects each fetch -> `<For>` keys by reference; use `reconcile()` on a store to diff-merge so identical items keep their DOM. Or `<Index>` if only values change.
- Effect runs immediately/at wrong time or infinite loops -> `createEffect` runs after render and on every tracked dep; don't write a signal it reads without `untrack`/guard; use `on(dep, fn, {defer:true})` to skip initial run.
- Reading a signal in an event handler and expecting it to "subscribe" -> handlers aren't tracking scopes; reads are one-time. That's usually correct — read latest value on click.
- Async/await inside `createEffect` loses tracking after `await` -> only synchronous reads before the first `await` are tracked. -> use `createResource`, or read deps before awaiting.
- Multiple `setState`/`setSignal` causing several updates -> wrap in `batch(() => {...})` (or a single store path set) to coalesce.
- SSR/hydration mismatch in SolidStart -> don't access `window`/`document` at module or component-body top level; use `onMount` or `isServer` guard.
- Conditional signal read hidden behind `&&` in JSX not updating -> ensure the tracked signal is called inside the reactive expression; prefer `<Show when={x()}>`.
- Storing/reading a signal getter without calling triggers "function rendered as text" -> always invoke `sig()` in JSX.
- `useContext` returns the default value -> component isn't wrapped in the `.Provider`, or provider is a sibling not ancestor.
- Spreading props to a child (`<Child {...props}/>`) loses fine-grained reactivity for some libs -> Solid handles spreads reactively via `mergeProps`, but don't pre-destructure before spreading.
- `<For>` index `i` is a signal (`i()`) but item is static; `<Index>` item is a signal (`item()`) but index is static -> pick based on whether identity or position is stable.
- Setting a store by mutating the proxy directly (`state.x = 1`) outside `produce` -> won't be tracked/immutable-safe; use `setState` path or `produce`.
- Ternary/`&&` in JSX evaluating both branches eagerly -> use `<Show>`/`<Switch>` so only the active branch's DOM is created and reactive.
- Reading a memo/signal at component top-level for a value expected to update UI -> body runs once; move the read into JSX or an effect.
