# Remix / React Router v7 (data + framework mode)

## Context
- Remix merged into **React Router v7**. Same primitives: `loader` (read) + `action` (write) + nested routes. "Framework mode" (Vite plugin, file routes, SSR) ≈ old Remix; "data mode" = `createBrowserRouter` with route objects; "declarative mode" = classic `<Routes>` (no data APIs). APIs below apply to framework/data mode.

## Loaders (server-side data reads)
```ts
// route module
export async function loader({ request, params }: LoaderFunctionArgs) {
  const user = await db.user.find(params.id);
  if (!user) throw new Response('Not found', { status: 404 });
  return { user };            // v7: return plain object (or Response)
}
export default function Route() {
  const { user } = useLoaderData<typeof loader>();
}
```
- Runs on the **server** (framework mode) before render; browser nav re-invokes via fetch. Safe for DB/secrets. `params` = dynamic segments, `request` = Web `Request` (read `new URL(request.url).searchParams`).
- Throw a `Response`/`redirect()` to short-circuit to error boundary / navigate. `redirect('/login', {status:302})`.
- All matched route loaders run **in parallel** on navigation (avoids parent->child waterfalls).

## Actions (writes / mutations)
```ts
export async function action({ request }: ActionFunctionArgs) {
  const form = await request.formData();
  const title = String(form.get('title'));
  const errors = validate(title);
  if (errors) return { errors };          // stays on page, re-renders
  await db.todo.create({ title });
  return redirect('/todos');
}
```
- Triggered by `<Form method="post">` submit or `useSubmit`/`fetcher.submit`. After a successful action, React Router **auto-revalidates all loaders** on the page (data stays fresh) — no manual refetch.
- Get action result in component via `useActionData<typeof action>()`. Method routing: check `request.method`.

## Forms + progressive enhancement
- `<Form method="post" action="/x">` — works without JS (native form POST -> action), enhanced to client fetch when JS loads. `<Form>` navigates (updates URL/history); avoid for background ops.
- `useFetcher()` — mutation/load **without navigation** (no URL change): `fetcher.Form`, `fetcher.submit(data,{method:'post'})`, `fetcher.load('/route')`, `fetcher.state` (`idle|submitting|loading`), `fetcher.data`. Use for likes, add-to-cart, autosave, type-ahead — multiple concurrent fetchers each track own state.
- `useNavigation()` — global nav/pending state (`navigation.state`, `navigation.formData`) for spinners on `<Form>` submits. `useSubmit()` for programmatic submit.
- **Optimistic UI**: read `fetcher.formData`/`navigation.formData` to render the pending value before the server responds; reconcile when real data lands.

## Nested routes + layouts
- File routes (framework mode) `app/routes/`: `todos.tsx` (parent, renders `<Outlet/>`), `todos.$id.tsx` (child at `/todos/:id`), `todos._index.tsx` (index at `/todos`). Dot = URL segment; `$` = dynamic param; `_layout` pathless layout; `($lang)` optional. Or config in `app/routes.ts` with `route()`, `layout()`, `index()`.
- Parent route renders shared UI + `<Outlet/>`; child renders inside. Each level has its own loader/action/error boundary. Layout state persists across child navigations (parent doesn't remount).
- `useOutletContext()` to pass data parent->child outlet. `useRouteLoaderData('routeId')` to read an ancestor's loader.

## Error boundaries
- `export function ErrorBoundary(){ const err = useRouteError(); if (isRouteErrorResponse(err)) {...4xx...} }` per route module. A thrown error/Response in a loader/action/render is caught by the **nearest** route ErrorBoundary; siblings/parents still render (localized failure). Root ErrorBoundary is the last resort.

## Deferred data + streaming (SSR)
- Return a promise (not awaited) to stream: `return { fast, slow: getSlow() }` (v7 auto-serializes promises). Render with `<Suspense fallback={...}><Await resolve={data.slow}>{v => ...}</Await></Suspense>`. First byte ships fast content; slow resolves stream in.
- Use for slow/non-critical data so the page isn't blocked by the slowest query. `useAsyncError()` inside `<Await errorElement>`.

## Sessions / cookies (server)
- `createCookieSessionStorage({cookie:{name,secrets,secure,httpOnly,sameSite}})` -> `getSession`, `commitSession`, `destroySession`. In loader: `const session = await getSession(request.headers.get('Cookie'))`; set `session.set('userId',id)`; return with `headers:{'Set-Cookie': await commitSession(session)}`. Flash: `session.flash(key,msg)`. Auth guard = check session in loader, `throw redirect('/login')`.

## meta / links / headers
- `export function meta({data}){ return [{title:data.user.name}, {name:'description',content:'...'}] }` per route -> `<title>`/meta tags (leaf overrides). `export function links(){ return [{rel:'stylesheet', href}] }`. `export function headers(){ return {'Cache-Control':'max-age=300'} }`.
- Root module renders `<Meta/>`, `<Links/>`, `<Scripts/>`, `<ScrollRestoration/>` in the HTML document shell.

## Revalidation control
- Default: loaders revalidate after every action + on navigation. Opt out/tune with `shouldRevalidate({currentUrl,formAction,defaultShouldRevalidate})` per route (return false to skip refetch — perf for expensive loaders). `useRevalidator()` to force manual revalidation.

## Client loaders / actions + prefetch
- `clientLoader`/`clientAction` (framework mode) run in the **browser** — cache, call server loader via `serverLoader()`, or do client-only work. `clientLoader.hydrate = true` to run on initial load. Use for optimistic caching / skipping server round-trips.
- `<Link prefetch="intent">` (or `render`/`viewport`) preloads a route's loader data + assets on hover/focus -> instant navigation. `<PrefetchPageLinks/>`.
- `useNavigate()` for programmatic nav; `useSearchParams()` for query state (setter triggers loader revalidation); `useMatches()` to read all active route data (breadcrumbs).

## Hooks / config quick ref
- `useLoaderData`, `useActionData`, `useRouteError`, `useNavigation`, `useFetcher`, `useFetchers` (all active), `useSubmit`, `useRevalidator`, `useParams`, `useSearchParams`, `useMatches`, `useOutletContext`, `useRouteLoaderData`, `useBlocker` (unsaved-changes guard).
- Route module exports: `loader`, `action`, `clientLoader`, `clientAction`, `default` (component), `ErrorBoundary`, `HydrateFallback`, `meta`, `links`, `headers`, `handle`, `shouldRevalidate`.

## Data mode (no framework/Vite plugin)
- `createBrowserRouter([{path, loader, action, element, errorElement, children}])` + `<RouterProvider router={router}/>`. Same loader/action/`useLoaderData` APIs, route objects instead of files, no SSR by default. `defer`/`Await` still available. Migrate declarative `<Routes>`/`<Route>` apps by moving data-fetching into `loader`.

## Gotchas -> Fix
- Using a loader for a mutation (or GET form that writes) -> loaders must be side-effect-free reads; writes go in `action` via POST. GET `<Form>` = navigation/filter only.
- Waterfall: child loader awaits data the parent already fetched, or sequential `await` in one loader -> loaders run in parallel across routes; within a loader use `Promise.all`; don't fetch a route's own data through a parent.
- `<Form>` for a background action reloads/navigates the page -> use `useFetcher().Form` (no navigation) for in-place mutations.
- Secrets/DB code bundled to client -> loader/action run server-only, but a module imported by the component ships to browser. Keep server-only code in `.server.ts` files or inside loader/action.
- `useActionData`/`useLoaderData` undefined -> action returned nothing / wrong route; type with `<typeof loader>`; ensure the component is the route's default export.
- Stale data after mutation -> normally auto-revalidates; if you disabled it via `shouldRevalidate`, call `useRevalidator()` or return true for that case.
- Thrown plain `Error` vs `Response` -> `throw new Response(null,{status:404})` for expected HTTP states (use `isRouteErrorResponse`); thrown `Error` = unexpected 500.
- Deferred `<Await>` never resolves / blocks -> don't `await` the promise in the loader (that defeats streaming); pass the raw promise and resolve in `<Await>` under `<Suspense>`.
- Redirect not working from action -> `return redirect(...)` (don't just call it); throwing also works. Cookies: include `Set-Cookie` in the redirect's `headers`.
- Loader re-runs on every keystroke via type-ahead `<Form>` -> use `fetcher.load`/`useFetcher` + debounce instead of navigation.
- Optimistic UI flickers -> reconcile `fetcher.formData` with server response; key list items stably; clear optimistic state once `fetcher.state==='idle'`.
- File route naming confusion (`todos.$id.tsx` vs folders) -> dots create URL segments, `$` = param, `_index` = index route, leading `_` = pathless layout; verify with the routes manifest.
- `clientLoader` runs but server `loader` data missing on first load -> set `clientLoader.hydrate = true` and provide a `HydrateFallback`, or call `serverLoader()` inside it.
- Parent route loader re-runs on every child navigation (expensive) -> `shouldRevalidate` returning false when only child params change.
- Reading `useSearchParams` mutations don't refetch -> setting search params IS a navigation and revalidates loaders; that's expected — debounce for type-ahead.
- Nested ErrorBoundary swallows an error you wanted at the root -> boundary catches at the nearest route; put critical handling higher or re-throw.
- `HydrateFallback` vs `ErrorBoundary` confusion -> `HydrateFallback` shows while `clientLoader` runs on hydration (no server data); `ErrorBoundary` catches thrown errors.
