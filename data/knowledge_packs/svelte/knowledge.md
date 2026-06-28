# Svelte Quick Reference

## Component (`.svelte`)
One file = `<script>` logic + markup + `<style>`. Styles are **scoped to the component** by default. Use `:global(...)` to escape scoping.

## Reactivity — SVELTE 5 RUNES (current)
- `let count = $state(0)` — reactive state; mutate freely: `count++`, `arr.push(x)` works (deep proxy).
- `let dbl = $derived(count * 2)` — computed; use `$derived.by(() => {...})` for blocks.
- `$effect(() => { ... })` — runs after DOM updates when read deps change; return a cleanup fn.
- `let { name, n = 0 } = $props()` — receive props; `$bindable()` for two-way props.

## Reactivity — CLASSIC (Svelte 3/4)
- `let count = 0` + **reassign** to update UI.
- `$: doubled = count * 2` — reactive declaration; `$: { ... }` reactive statement. Re-runs only when **referenced vars** change.
- `export let prop` — declare a prop; `export let prop = 'default'`.

## Markup blocks
```
{#if a}..{:else if b}..{:else}..{/if}
{#each items as item, i (item.id)}..{:else}empty{/each}
{#await promise}..{:then v}..{:catch e}..{/await}
{@html rawString}  {@const x = ...}
```
Always key `{#each}` for correct reordering.

## Events
- Svelte 5: `<button onclick={handler}>` (plain prop).
- Classic: `<button on:click={handler}>`, modifiers `on:click|preventDefault|once`.
- v5: call `e.preventDefault()` in handler (no modifiers).

## Binding
- `<input bind:value={name}>` two-way; also `bind:checked`, `bind:group`, `bind:files`.
- `<div bind:this={el}>` — get DOM node reference.

## Stores (cross-component)
```js
import { writable } from 'svelte/store';
export const count = writable(0);
```
- `count.set(1)`, `count.update(n => n+1)`.
- In components, `$count` auto-subscribes/unsubscribes and is reactive.
- `readable`, `derived` also available. (Runes apps often prefer `$state` in a `.svelte.js` module instead.)

## Lifecycle
`import { onMount, onDestroy } from 'svelte'` — `onMount(() => {... return cleanup })`. In v5, `$effect` covers most mount/cleanup needs.

## Transitions
`import { fade } from 'svelte/transition'` -> `<div transition:fade={{duration:200}}>`; `in:`/`out:` for one direction; `animate:flip` for keyed lists.

## GOTCHAS (with fixes)
- **Classic is assignment-triggered:** `arr.push(x)` / `obj.k=v` do NOT update. Fix: reassign `arr = [...arr, x]`; `obj = {...obj, k:v}`. (Or use `$state` in v5 — mutation just works.)
- **`$:` misses deps:** only re-runs on variables it directly references; a value read inside a called function may not trigger it.
- **Don't mutate props:** props are owner-owned; mutating breaks one-way flow. Use callbacks/events or `bind:`/`$bindable`.
- **Store value != `$store`:** `count` is the store object; `$count` is its value. Outside components use `get(count)` or subscribe.
- **`$effect` runs only after mount** and tracks only synchronously-read deps.
