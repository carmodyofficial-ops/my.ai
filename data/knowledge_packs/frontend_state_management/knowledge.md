# Frontend State Management

## Pick the right bucket first
- **Server state** (data owned by an API: users, orders): use TanStack Query / SWR / RTK Query — caching, dedupe, refetch, invalidation. Do NOT mirror it into Redux/zustand.
- **Client/UI state** (modals, filters, drafts): component `useState` first; lift only as far as needed; global store only for truly cross-cutting state (theme, auth session, cart).
- **URL state** (search, filters, pagination, selected tab): put it in the query string — shareable, back-button-friendly, survives refresh.
- **Form state**: react-hook-form (uncontrolled, per-field subscriptions, minimal re-renders) or native `FormData` for simple cases.
- Most "we need Redux" apps need: TanStack Query + URL params + a 50-line zustand store.

## TanStack Query (React Query)
- `useQuery({ queryKey: ['todos', filters], queryFn, staleTime: 60_000 })` — key must include every variable the fetch depends on; changing key = new cache entry + fetch.
- `staleTime` (default 0): how long data is fresh — no background refetch while fresh. `gcTime` (default 5 min): how long unused cache lives. Most apps should raise `staleTime`; default 0 refetches on every mount/window-focus.
- Invalidation after mutation: `useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['todos'] }) })` — prefix-matches all `['todos', ...]` keys.
- Optimistic updates: `onMutate` snapshot + `setQueryData`, roll back in `onError` with the snapshot, `invalidateQueries` in `onSettled`.
- `enabled: !!userId` for dependent queries; `placeholderData: keepPreviousData` for pagination without flicker; `select` to subscribe to a slice and cut re-renders.

## zustand
- `const useStore = create((set) => ({ count: 0, inc: () => set((s) => ({ count: s.count + 1 })) }))` — no provider needed.
- Always select slices: `useStore((s) => s.count)`; selecting the whole store re-renders on every change. Object selectors need `useShallow` (zustand v5) to avoid re-render on new-object identity.
- `set` shallow-merges top level only — nested updates must spread: `set((s) => ({ user: { ...s.user, name } }))`, or use the `immer` middleware.
- Read without subscribing (in callbacks/handlers): `useStore.getState()`.
- Middleware: `persist` (localStorage; mind hydration timing in SSR), `devtools` (Redux DevTools), `subscribeWithSelector`.

## Redux Toolkit (RTK)
- `createSlice({ name, initialState, reducers })` — reducers "mutate" via Immer; never mutate outside createSlice.
- Async: `createAsyncThunk` + `extraReducers` handling `pending/fulfilled/rejected`; or prefer RTK Query (`createApi`) for server data — tags (`providesTags`/`invalidatesTags`) drive cache invalidation.
- Selectors with `createSelector` (reselect) memoize derived data; returning a fresh array/object from `useSelector` every call causes re-renders — memoize or use `shallowEqual`.
- Non-serializable values (Dates, class instances, promises) in the store trigger middleware warnings and break devtools/persist — keep the store plain JSON.

## React Context tradeoffs
- Context is dependency injection, not a state manager: every consumer re-renders when the value changes — no selectors, no partial subscription.
- Fine for rarely-changing values: theme, locale, auth user, a stable store instance.
- Mitigations: split contexts by change-frequency (state vs dispatch), memoize the provider `value` (`useMemo`) — an inline object literal re-renders all consumers on every parent render.
- High-frequency shared state (cursor, live prices, keystrokes) → external store (zustand/jotai) with subscriptions, not Context.

## URL as state
- React Router: `const [params, setParams] = useSearchParams(); setParams(prev => { prev.set('page', '2'); return prev }, { replace: true })` — `replace` avoids history spam for filters.
- Next.js App Router: read `useSearchParams()`, write via `router.replace(pathname + '?' + qs)`; serialize with `URLSearchParams`.
- Encode: primitives and short lists only; validate/parse on read (zod) because users edit URLs.
- nuqs (React) gives typed `useQueryState('page', parseAsInteger.withDefault(1))`.

## Signals (concept)
- Fine-grained reactivity: a signal is a value + subscription; computations track which signals they read and re-run only on those changes — no component-tree re-render diffing. Solid, Preact Signals, Vue `ref`, Angular signals.
- `const count = signal(0); const double = computed(() => count.value * 2); effect(() => log(count.value))`.
- React has no native signals; Preact Signals' React adapter works but fights React's model — prefer zustand/jotai (jotai atoms ≈ signal ergonomics) inside React.

## Derived state & structure
- Never store what you can compute: `const visible = todos.filter(...)` in render (memoize with `useMemo` only if measurably hot) — storing `visibleTodos` alongside `todos` invites desync.
- Normalize collections in stores: `{ byId: Record<string, T>, allIds: string[] }` (RTK `createEntityAdapter`) — O(1) updates, no deep array surgery.
- Keep stores flat and action-oriented: expose `addItem(item)`, not `setItems(fn)` — callers shouldn't know the shape.
- Reset-on-logout: zustand `useStore.setState(initialState, true)` (replace flag) or an RTK root reducer that returns undefined state on a `logout` action; also `queryClient.clear()`.
- Cross-tab sync: `persist` + the `storage` event, or `BroadcastChannel`; TanStack Query has `broadcastQueryClient` (experimental).
- jotai in one line: atoms are tiny independent stores (`const countAtom = atom(0)`); derived atoms (`atom(get => get(a) + get(b))`) give signal-like granularity with React idioms.

## Gotchas -> Fix
- **Server data copied into useState/useEffect ("fetch-then-set")**: loses caching, races on fast navigation — use useQuery; if you must, add an abort/ignore flag in the effect cleanup.
- **Everything re-renders on one Context change**: split contexts, memoize `value`, or move to a store with selectors.
- **TanStack Query refetch storm on window focus**: raise `staleTime`; disable `refetchOnWindowFocus` only if the data is genuinely static.
- **Mutation succeeded but list stale**: no invalidation — `invalidateQueries` with the list's key prefix in `onSuccess`/`onSettled`.
- **zustand selector returns new object each render** (`(s) => ({a: s.a, b: s.b})`): infinite/extra re-renders — wrap with `useShallow` or select primitives separately.
- **Redux state update not re-rendering**: reducer mutated state outside Immer or returned the same reference — always produce new references (or stay inside createSlice).
- **Filters reset on refresh/back**: state lived in memory — move to URL search params.
- **Form re-renders whole page per keystroke**: controlled inputs at top level — use react-hook-form (`register`) or isolate the form in a child component.
- **Persisted zustand store hydrates after first render (SSR mismatch)**: gate UI on a `hasHydrated` flag via `onRehydrateStorage`.
- **Query key misses a dependency**: two different filters share one cache entry — include every input in `queryKey`.
