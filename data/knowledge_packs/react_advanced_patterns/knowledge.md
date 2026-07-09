# React Advanced Patterns & Internals

## Reconciliation & keys (deep)
- Diff is per-sibling-list and per-type: element `type` change (e.g. `div`→`span`, or `ComponentA`→`ComponentB`) unmounts the whole subtree, discarding state + DOM. Same type → in-place update, props diffed.
- `key` identity is scoped to siblings under one parent only; not global. Reordering keyed children moves fibers, preserving state; index keys break this — inserting at head reuses wrong fiber, causing state/input bleed and wasted DOM writes.
- Force remount on prop change: give element a `key` derived from that prop (`<Editor key={docId}/>`) to reset all internal state — cleaner than a `useEffect` reset.
- Two elements at the same position with different `key` = unmount+mount even if same type. Conditional `{cond ? <A/> : <B/>}` where A/B share type keeps state unless keys differ.
- Fiber tree: two trees (`current` + `workInProgress`); commit swaps them (double-buffering). Render phase is interruptible/restartable in concurrent mode → render must be pure (no side effects, no mutation of module state).

## Bailout & memoization
- Bailout: if a component renders and returns the *same element reference* (React skips it), OR if `React.memo` shallow-equal props hold, React reuses the prior fiber and skips re-render of that subtree. Passing `children` as a stable prop from a non-re-rendering parent is a zero-cost "memo": `<Heavy>{stableChildren}</Heavy>`.
- `React.memo(Cmp, areEqual?)`: shallow-compares props; breaks the moment a prop is a fresh object/array/function each render. Pair with `useCallback`/`useMemo` on the parent to keep referential identity.
- `useMemo`/`useCallback` guarantee identity *only if deps are stable*; they are caches, not correctness. Not guaranteed to persist (React may drop under memory pressure) — never rely on them for one-time side effects.
- Common mistake: memoizing a component but still passing `style={{...}}` or `onClick={()=>...}` inline → memo never hits. Also `context` value changes bypass memo entirely (consumers re-render regardless).
- State setter identity is stable; `ref` object identity is stable; `dispatch` is stable — safe to omit from deps (and to pass without `useCallback`).

## Concurrent React
- `useTransition()` → `[isPending, startTransition]`. Marks the state update inside `startTransition(fn)` as low-priority/interruptible; keeps the old UI interactive while the transition renders in the background. `isPending` flags the in-flight state.
- `startTransition` (standalone import) same but no pending flag; only synchronous updates inside the callback are marked (async ones after `await` are NOT — wrap the setter after await in another `startTransition`).
- `useDeferredValue(value)` returns a lagging copy; on urgent update React renders with old deferred value first, then re-renders with new one at low priority. Use for expensive derived UI (filtered lists). Combine with `React.memo` on the consumer or the deferral does nothing.
- Concurrent features require the state update be replayable → keep reducers/render pure. Transitions can be abandoned/restarted, so effects still fire only on commit, not on discarded renders.
- Suspense: a component suspends by throwing a promise (data libs / `React.lazy` / RSC). Nearest `<Suspense fallback>` shows fallback; on resolve, React retries render. Transitions suppress the fallback (keep showing stale content) → avoid jarring spinners.
- Streaming SSR: `renderToPipeableStream` (Node) / `renderToReadableStream` (edge). Shell flushes first; suspended boundaries stream in later as inline `<script>` that swaps placeholder → real content. Selective hydration: React hydrates boundaries independently, prioritizing the one the user interacts with.

## Server Components & actions
- RSC render on server only, never ship JS, can be `async` + `await` data directly, and cannot use state/effects/browser APIs/event handlers. `"use client"` marks the boundary: everything imported *into* a client module is client code. Props crossing server→client must be serializable (no functions except server actions, no class instances).
- Client components can render server components only via `children`/props (composition), not by importing them directly.
- Server Actions (`"use server"`): async functions callable from client (form `action`, or invoked in event handlers/transitions). Run on server, can mutate + `revalidatePath`/`revalidateTag`. Arguments and return serialized. Never trust inputs — they're a public POST endpoint; authorize inside.

## Context performance
- Any context value change re-renders ALL consumers regardless of which slice they read. Fix: split into multiple contexts (state vs dispatch; per-domain), and memoize the provider `value`.
- Selector pattern: store a ref/external store and expose a hook that subscribes with a selector; or use `use-context-selector`. Vanilla context has no selector.
- Stable-dispatch pattern: separate `StateContext` and `DispatchContext` so action-only consumers never re-render on state change.

## useSyncExternalStore & tearing
- `useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot?)` — the correct way to read external mutable stores under concurrent rendering; prevents *tearing* (two components in one commit showing different store values) by forcing a synchronous consistent read.
- `getSnapshot` must return a referentially-stable value when unchanged (cache it) or you get infinite loops / needless renders. `getServerSnapshot` required for SSR to avoid hydration mismatch.
- Deriving state via `useState`+`useEffect` subscription tears under concurrent features — migrate stores to `useSyncExternalStore`.

## Refs & imperative handles
- `useImperativeHandle(ref, () => ({...}), deps)` exposes a curated imperative API instead of the DOM node; pair with `forwardRef` (pre-19) — in React 19 `ref` is a normal prop.
- Callback refs run on mount (node) and unmount (null); React 19 supports returning a cleanup fn from a callback ref. Measuring layout: callback ref fires before paint, better than `useEffect` for immediate measure.
- `useRef` mutation does not trigger render and is not tracked; reading `ref.current` during render is impure (except for lazy-init pattern).

## Compound components / render props vs hooks
- Compound components: parent shares implicit state via context to children (`<Tabs><Tab/></Tabs>`); flexible composition without prop drilling. Use `React.Children`/context, not cloneElement scanning (fragile).
- Render props and HOCs largely superseded by hooks for logic reuse; render props still valid for *rendering* control (pass a render fn). Hooks can't conditionally share JSX; render props can.

## Effects & StrictMode
- StrictMode (dev only) double-invokes render, effects (mount→cleanup→mount), and reducers to surface impurity + missing cleanup. Production runs once. Don't "fix" by disabling StrictMode — fix the effect.
- Effect cleanup must cancel in-flight async (AbortController / ignore-flag) to prevent race: fast prop changes fire overlapping fetches; last-to-resolve may not be last-requested → stale render. Track a mutable `ignore` flag per effect run.
- `useLayoutEffect` runs synchronously after DOM mutation, before paint (use for measurement/DOM sync to avoid flicker); blocks paint → keep cheap. SSR warns on `useLayoutEffect` (no DOM) — guard or use `useInsertionEffect` for CSS-in-JS.
- Effects with object/array deps re-run every render (new identity) — memoize deps or restructure. Missing deps → stale closures capturing old state.

## Profiling
- React DevTools Profiler: "Record why each component rendered" reveals props/state/hooks/parent-caused renders. Flame chart width = render cost; look for wide bars re-rendering on unrelated updates → memo boundary needed. "Highlight updates when components render" for visual thrash.
- `<Profiler onRender={(id, phase, actualDuration, baseDuration)=>...}>` — `baseDuration` = no-memo cost estimate; `actual` ≪ `base` means memo is working.

## Gotchas -> Fix
- Index keys on reorderable/removable lists → wrong item keeps state, form inputs swap values → **use stable domain IDs as keys**.
- `React.memo` "not working" → an inline object/array/fn prop or a context change → **stabilize props (`useMemo`/`useCallback`) and check context consumers**.
- State update after `await` inside `startTransition` not treated as transition → **re-wrap the post-await setter in `startTransition`**.
- `useDeferredValue` gives no benefit → consumer not memoized, so it re-renders on the urgent pass anyway → **wrap the expensive consumer in `React.memo`**.
- `getSnapshot` returns fresh object each call → infinite render loop in `useSyncExternalStore` → **memoize/ cache the snapshot; return the same ref when unchanged**.
- Reading/mutating a ref or module variable during render → breaks concurrent replay, tearing → **do it in effects/event handlers; render stays pure**.
- Passing a server component as an import into a client component → build error → **pass it as `children` from a server parent**.
- Non-serializable prop across the server/client boundary (Date methods, functions, class instances) → serialization error → **send plain data; move behavior to client or a server action**.
- Server action assumed authenticated because it's "internal" → it's a public endpoint → **re-authenticate/authorize + validate inside every action**.
- Suspense fallback flashes on every navigation/update → **wrap the triggering update in a transition so React keeps stale UI**.
- Deriving state from props with `useEffect`+`setState` → extra render + tearing → **compute during render, or `key`-remount, or `useMemo`**.
- Overlapping fetches in an effect leave stale data → **AbortController or `ignore` flag in cleanup; key requests by args**.
- `useMemo` used to skip a side effect (e.g. logging) → cache may be dropped/re-run → **never; effects go in `useEffect`**.
- Context provider value `{a,b}` inline → all consumers re-render each parent render → **`useMemo` the value; split contexts**.
- StrictMode "double fetch" alarms → it's dev-only surfacing a missing cleanup/idempotency → **make the effect idempotent + cancelable, not disable StrictMode**.
