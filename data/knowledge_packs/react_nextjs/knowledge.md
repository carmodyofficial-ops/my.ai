# React + Next.js

## React: Components & Hooks
- Function components only. State via `useState`; group related state or use `useReducer` for multi-field transitions.
- `useEffect` is for **side effects + external sync** (subscriptions, DOM, non-React widgets). Not for transforming props/state — derive during render: ``const full = `${first} ${last}` ``.
- Deps array: list every reactive value used. Cleanup with a return: `useEffect(()=>{const id=setInterval(t);return()=>clearInterval(id)},[])`.
- `useMemo`/`useCallback` only for measured perf or referential stability (deps of effects, memoized children). Don't wrap everything.
- `useRef` for mutable values that don't trigger render (timers, DOM nodes, previous values). Changing `.current` never re-renders.
- Props down, lift shared state to nearest common parent. Cross-tree state -> `Context` (sparingly; it re-renders all consumers on any value change — split contexts or memoize the value). Extract reusable stateful logic into custom hooks (`useX`).
- Hooks only at top level — never in conditions, loops, or after early returns.

## React: Rendering
- Stable keys from data id: `key={item.id}`. **Never `key={index}`** when lists reorder/insert/delete — causes wrong state reuse.
- Conditional: `{cond && <X/>}` (guard against `0` rendering — use `cond ? <X/> : null` or `!!cond &&`).
- Controlled inputs: `<input value={v} onChange={e=>setV(e.target.value)}/>`. Uncontrolled: `defaultValue` + ref.
- State updates are batched; `setX(v)` doesn't change `x` in the current closure — reads after `set` see the old value.
- Changing a component's `key` remounts it (resets all state) — useful to reset forms per record.

## Next.js App Router
- Server Components by default: `async function Page(){const d=await fetch(url,{next:{revalidate:60}}); ...}` — no `useEffect`, no client fetch, no hooks that need the browser.
- `"use client"` only for state/effects/event handlers/browser APIs. Put it at leaves; pass server data as props. A client component's imports all become client code — but it can still render server components passed as `children`.
- File conventions in `app/`: `page.tsx` (route UI), `layout.tsx` (persists across navigations, doesn't re-render), `loading.tsx` (Suspense fallback), `error.tsx` (must be `"use client"`), `not-found.tsx`, `route.ts` (API handler: `export async function GET(req)`).
- Dynamic segments: `app/posts/[slug]/page.tsx` -> `params.slug`; catch-all `[...slug]`. Pre-render with `generateStaticParams`.
- Navigation: `<Link href>` (prefetches), `useRouter().push()` from `next/navigation` (not `next/router`), `redirect()`/`notFound()` in server code.
- SEO: export `metadata` object or `generateMetadata({params})`.

## Data fetching, caching, revalidation
- Fetch in Server Components, as close to where data is used as possible — React dedupes identical `fetch` calls per render pass.
- Cache control per request: `fetch(url,{cache:'no-store'})` (always fresh), `{next:{revalidate:60}}` (ISR-style), `{next:{tags:['posts']}}` then `revalidateTag('posts')`.
- Route-level: `export const dynamic = 'force-dynamic'` (no static), `export const revalidate = 60`.
- Mutations via **server actions**: `"use server"` function, call from a form `action={fn}` or client handler; after writing, `revalidatePath('/posts')` or `revalidateTag(...)` — otherwise the UI shows stale cached data.
- Server actions receive `FormData` from forms: `async function create(formData){ 'use server'; const t = formData.get('title'); }`. Pending UI: `useFormStatus` in a child of the form; `useActionState` for returned errors.
- Reading request data in server code: `cookies()`, `headers()` from `next/headers` — using them opts the route into dynamic rendering.

## Suspense & streaming
- `loading.tsx` wraps the page in a Suspense boundary — shell streams immediately, page streams when ready.
- Finer-grained: wrap slow children in `<Suspense fallback={<Skeleton/>}>` and make the child an async server component; siblings render immediately.
- Don't `await` everything at the top of a page sequentially (waterfall) — start promises in parallel (`Promise.all`) or pass promises down and `use(promise)`/await in the child under its own Suspense boundary.
- `error.tsx` catches render errors below it and gets `{error, reset}`; it does not catch errors in the layout beside it.

## Middleware
- `middleware.ts` at project root; runs before every matched request (edge runtime — no Node APIs).
- `export const config = { matcher: ['/dashboard/:path*'] }` to scope; without a matcher it runs on everything including assets.
- Use for auth redirects, locale routing, header rewrites: `NextResponse.redirect(new URL('/login', req.url))`, `NextResponse.next()`.
- Keep it thin — no DB calls; check a cookie/JWT and redirect. Heavy auth belongs in the route/layout.

## Performance & Next.js extras
- `React.memo(Child)` only when profiling shows re-render cost; pair with stable props (`useCallback`/`useMemo`). `useTransition`/`startTransition` keeps typing responsive during heavy state updates; `useDeferredValue` for derived expensive lists.
- Code-split client-heavy widgets: `const Chart = dynamic(() => import('./Chart'), { ssr: false, loading: () => <Spinner/> })`.
- `next/image` requires `width`/`height` (or `fill` + sized parent); remote hosts must be whitelisted in `next.config.js` `images.remotePatterns`. `next/font` self-hosts fonts, no layout shift.
- Route handlers (`route.ts`): return `Response.json(data)`; `GET` with no dynamic reads is cached statically — add `export const dynamic='force-dynamic'` if it must run per request.
- Parallel (`@slot`) and intercepting (`(.)`) routes power modals-with-URL patterns; know they exist before hand-rolling.

## Gotchas -> Fix
- **Stale closure**: handler/effect reads old state. Fix: add to deps, or functional update `setN(n=>n+1)`.
- **Missing deps**: trust eslint-plugin-react-hooks; don't silence — restructure (move fn inside effect, or `useCallback`).
- **Effect for derived state**: delete the effect, compute in render (memoize if expensive).
- **setState during render** -> infinite loop. Move into handler/effect; or for reset-on-prop-change, use a `key` or compare-and-set pattern.
- **Hydration mismatch**: no `Date.now()`/`Math.random()`/`window`/locale formatting in server render; gate with mounted flag (`useEffect(()=>setMounted(true),[])`) or `suppressHydrationWarning` on the specific node. Also caused by invalid HTML nesting (`<div>` inside `<p>`).
- **`window is not defined` at build**: module-scope browser API in a file that renders on the server. Fix: move into `useEffect`, or `next/dynamic` with `ssr:false`.
- **Client fetch that could be server**: move to a Server Component; less JS, no loading spinner.
- **Passing non-serializable props** (functions, class instances, Dates pre-Next 15 actions) from server to client component -> error. Pass plain data; for callbacks pass server actions.
- **Importing server-only code into client** (DB clients, secrets): add `import 'server-only'` to server modules so the build fails loudly instead of leaking.
- **Env vars undefined in browser**: only `NEXT_PUBLIC_`-prefixed vars are inlined client-side; they're baked at **build** time, not runtime.
- **Everything renders dynamic unexpectedly**: a `cookies()`/`headers()`/`searchParams` read high in the tree opts pages out of static. Isolate dynamic reads; check build output (`○` static vs `ƒ` dynamic).
- **Mutated but UI stale after server action**: missing `revalidatePath`/`revalidateTag`.
- **Router cache shows stale page after back-nav**: client router caches; `router.refresh()` re-fetches server components.
- **`useSearchParams` build error**: wrap the client component in `<Suspense>` — it forces CSR bailout otherwise.
- **Prop drilling**: lift to layout/Context or compose with `children` slots.
- **Giant `"use client"` at layout level**: kills server-component benefits for the whole subtree; push it down to interactive leaves.
- **Deploy: works locally, 500s in prod**: check runtime env vars exist on the host, and that filesystem writes aren't assumed (serverless FS is read-only except `/tmp`).
