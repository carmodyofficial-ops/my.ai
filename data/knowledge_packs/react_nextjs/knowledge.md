# React + Next.js

## React: Components & Hooks
- Function components only. State via `useState`; group related state or use `useReducer`.
- `useEffect` is for **side effects + external sync** (subscriptions, DOM, fetch in client). Not for transforming props/state — derive during render: ``const full = `${first} ${last}` ``.
- Deps array: list every reactive value used. Cleanup with a return: `useEffect(()=>{const id=setInterval(t);return()=>clearInterval(id)},[])`.
- `useMemo`/`useCallback` only for measured perf or referential stability (deps of effects, memoized children). Don't wrap everything.
- Props down, lift shared state to nearest common parent. Cross-tree state -> `Context` (sparingly; it re-renders all consumers). Extract reusable stateful logic into custom hooks (`useX`).

## React: Rendering
- Stable keys from data id: `key={item.id}`. **Never `key={index}`** when lists reorder/insert/delete — causes wrong state reuse.
- Conditional: `{cond && <X/>}` (guard against `0`), or ternary.
- Controlled inputs: `<input value={v} onChange={e=>setV(e.target.value)}/>`.

## Next.js (App Router)
- Server Components by default: `async function Page(){const d=await fetch(url,{next:{revalidate:60}});}` — no `useEffect`, no client fetch.
- `"use client"` only for state/effects/event handlers/browser APIs. Keep it at leaves; pass server data as props.
- Routing: `app/page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`. Mutations via **server actions** (`"use server"`), then `revalidatePath('/x')`.
- SEO: export `metadata` or `generateMetadata`.

## Gotchas -> Fix
- **Stale closure**: handler/effect reads old state. Fix: add to deps, or `setN(n=>n+1)` functional update.
- **Missing deps**: trust eslint-plugin-react-hooks; don't silence — restructure.
- **Effect for derived state**: delete the effect, compute in render.
- **setState during render** -> infinite loop. Move into handler/effect.
- **Hydration mismatch**: no `Date.now()`/`Math.random()`/`window` in server render; gate with `useEffect`+mounted flag or `suppressHydrationWarning`.
- **Client fetch that could be server**: move to a Server Component.
- **Prop drilling**: lift to layout/Context or compose with `children`.
