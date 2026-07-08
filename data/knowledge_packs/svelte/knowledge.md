# Svelte (runes + classic) + SvelteKit

## Component (`.svelte`)
- One file = `<script>` + markup + `<style>`. Styles are **scoped to the component**; escape with `:global(...)`. Unused selectors are dropped at compile time.

## Reactivity — SVELTE 5 RUNES (current)
- `let count = $state(0)` — reactive state; mutate freely: `count++`, `arr.push(x)` works (deep proxy). `$state.raw(obj)` for large non-mutated data (reassign only).
- `let dbl = $derived(count * 2)` — computed; `$derived.by(() => {...})` for multi-line. Deriveds are lazy + cached; never reassign inside.
- `$effect(() => {...})` — runs after DOM updates when synchronously-read deps change; return a cleanup fn. `$effect.pre` runs before DOM update.
- `let { name, n = 0, ...rest } = $props()` — props; two-way with `let { value = $bindable() } = $props()`.
- `$inspect(count)` — dev-only reactive console.log.
- Share reactive state across files: export `$state` from a `.svelte.js`/`.svelte.ts` module (export an object and mutate its properties — reassigning an exported `let` breaks cross-module reactivity).
- Snippets replace slots: `{#snippet row(item)}...{/snippet}` passed as props, rendered with `{@render row(x)}`; `{@render children?.()}` is the default-slot equivalent.

## Reactivity — CLASSIC (Svelte 3/4)
- `let count = 0` + **reassignment** triggers updates; `arr.push(x)` does NOT — reassign `arr = [...arr, x]`.
- `$: doubled = count * 2` reactive declaration; `$: {...}` statement; re-runs only when **directly referenced** vars change.
- `export let prop = 'default'` — props. Events: `createEventDispatcher()` + `on:save`.

## Markup blocks
```
{#if a}..{:else if b}..{:else}..{/if}
{#each items as item, i (item.id)}..{:else}empty{/each}
{#await promise}..{:then v}..{:catch e}..{/await}
{#key value}remounts on change{/key}   {@html raw}  {@const x = ...}
```
- Always key `{#each}` (`(item.id)`) for correct reorder/remove. `{@html}` = XSS if user data — sanitize.

## Events & binding
- Svelte 5: `<button onclick={handler}>` (plain prop; no modifiers — call `e.preventDefault()` yourself). Classic: `on:click`, modifiers `on:click|preventDefault|once`.
- `<input bind:value={name}>`; also `bind:checked`, `bind:group`, `bind:files`, `bind:this={el}` (DOM node), `bind:clientWidth`.
- Component two-way: `<Child bind:value>` requires `$bindable` (v5) or `export let` (classic).

## Stores (`svelte/store`) — classic, still valid in v5
- `export const count = writable(0)`; `count.set(1)`, `count.update(n=>n+1)`; `derived([a,b], ([$a,$b])=>...)`; `readable(0, set=>{...})`.
- In components `$count` auto-subscribes/unsubscribes and is assignable (`$count = 5`). Outside components: `get(count)` or manual `.subscribe` (remember to unsubscribe).
- Runes apps usually prefer `$state` in a `.svelte.js` module instead.

## Lifecycle & transitions
- `onMount(() => {...; return cleanup})` (client-only — safe place for `window`), `onDestroy`, `tick()` awaits pending DOM updates. In v5 `$effect` covers most mount/cleanup.
- `import { fade, fly, slide } from 'svelte/transition'` -> `<div transition:fade={{duration:200}}>`; `in:`/`out:` one-way; `animate:flip` for keyed list moves.

## SvelteKit
- Filesystem routing in `src/routes/`: `+page.svelte` (UI), `+page.js` (universal `load`), `+page.server.js` (server-only `load` + form `actions`), `+layout.svelte` (wraps children, persists), `+server.js` (API endpoint: `export function GET({url})` -> `json(data)`), `+error.svelte`.
- Dynamic routes: `src/routes/posts/[slug]/+page.svelte` -> `load({params})` gets `params.slug`; rest `[...path]`, optional `[[lang]]`.
- `load` returns data -> component receives it: v5 `let { data } = $props()`; classic `export let data`. Use the provided `fetch` in `load` (SSR-aware, relative URLs, dedupes). Layout data merges into page `data`.
- Server `load`/actions can touch DBs/secrets; universal `load` runs on server **and** browser — no secrets there. Server-only modules: `$lib/server/` or `$env/static/private`.
- Form actions: `export const actions = { default: async ({request}) => { const data = await request.formData(); return fail(400, {msg}) or redirect(303,'/x') } }`; `<form method="POST" use:enhance>` progressively enhances; result lands in `form` prop.
- Invalidate/refresh: `invalidate(url)`, `invalidateAll()`; `depends('app:key')` in load + `invalidate('app:key')`.
- Navigation: `<a href>` is client-routed automatically; `goto('/x')` programmatic; `$app/state` (v5) / `$app/stores` (`$page`) for current URL/params/data.
- Env: `$env/static/public` requires `PUBLIC_` prefix for client exposure; private vars are server-only and importing them client-side is a build error (good).
- Prerender/SSR toggles per route: `export const prerender = true`, `export const ssr = false`, `export const csr = false`.

## Advanced bits
- Actions — reusable element behavior: `function tooltip(node, text) { ...; return { update(t){}, destroy(){} } }` -> `<div use:tooltip={'hi'}>`. Ideal for third-party lib mounting, click-outside.
- Context: `setContext('key', value)` in a parent, `getContext('key')` in descendants — component-tree-scoped DI without prop drilling; pass a `$state` object for reactivity.
- Special elements: `<svelte:window onkeydown={...} bind:scrollY>`, `<svelte:head><title>...</title></svelte:head>`, `<svelte:element this={tag}>` dynamic tags, `<svelte:boundary>` (v5) for error boundaries.
- Class/style sugar: `class:active={isActive}`, `style:color={c}`; v5 also accepts `class={{ active }}` objects/arrays.
- SvelteKit hooks: `src/hooks.server.js` `handle({event, resolve})` for auth — populate `event.locals`, read it in server `load`. `handleFetch` rewrites SSR fetches.
- Adapters pick deploy target: `@sveltejs/adapter-auto`, `-node`, `-static` (full prerender; needs `prerender = true`), `-vercel`/`-cloudflare`.

## Gotchas -> Fix
- **Classic: mutation doesn't update UI**: `arr.push(x)`/`obj.k=v` are invisible. Fix: reassign (`arr=[...arr,x]`) — or use v5 `$state` where mutation just works.
- **`$:` misses deps**: it only tracks variables referenced **directly in the statement**; values read inside a called function don't trigger. Restructure to reference them inline.
- **v5: destructured `$state` loses reactivity**: `const {x} = stateObj` snapshots. Keep the object and read `stateObj.x`, or use `$derived`.
- **v5: exported `let` state reassigned across modules breaks**: export an object (`export const app = $state({user:null})`) and mutate properties.
- **`$effect` for derived values**: infinite-loop / lag smell. Use `$derived`; effects are for DOM/external sync only.
- **`state_unsafe_mutation` error**: mutating `$state` inside a `$derived` or template expression. Move the write to an effect/handler.
- **Don't mutate props**: owner-owned; use callbacks, events, or `bind:`/`$bindable`.
- **Store vs value**: `count` is the store object; `$count` is the value. Outside `.svelte` files use `get(count)`.
- **`window`/`document` during SSR** -> crash. Gate in `onMount`/`$effect`, or `import { browser } from '$app/environment'`.
- **Fetching in component instead of `load`** -> no SSR data, waterfalls. Move to `+page(.server).js`.
- **Secrets in universal `load`** (`+page.js`) leak to client — move to `+page.server.js`.
- **Form action mutated but page stale**: return path without redirect skips rerun — `use:enhance` re-runs load; otherwise `invalidateAll()`.
- **Shared module-level state on the server** leaks between users during SSR — keep per-request state in `locals`/`load`, not module scope.
- **Unkeyed `{#each}` with removals** -> wrong rows keep state. Add `(item.id)`.
- **`$effect` re-runs too often**: it tracks everything read synchronously — read-only-once values via `untrack(() => x)`.
- **DOM not updated right after state change**: updates are batched — `await tick()` before measuring the DOM.
- **`goto()` in server code fails**: server-side redirects use `redirect(303, '/x')` from `@sveltejs/kit`; `goto` is browser-only.
- **Scoped styles don't reach child components**: scoping stops at component boundaries — pass classes as props, use CSS custom properties, or `:global` narrowly.
