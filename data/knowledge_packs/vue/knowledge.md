# Vue 3 (Composition API + Options) + Pinia/Router/Nuxt

## `<script setup>` (SFC, recommended)
- One `.vue` file = `<template>` + `<script setup>` + `<style scoped>`. `scoped` isolates CSS to component; `:deep(sel)` pierces child; `:global(sel)`.
- Top-level bindings in `<script setup>` are auto-exposed to template. Imports/components used directly — no `components: {}` registration.
- Compiler macros (no import): `defineProps`, `defineEmits`, `defineModel`, `defineExpose`, `withDefaults`.

## Reactivity core
- `const c = ref(0)` — reactive box; read/write `.value` **in JS** (`c.value++`). In template it auto-unwraps: `{{ c }}`. Works for primitives + objects.
- `const s = reactive({a:1})` — deep-reactive proxy of an object; access `s.a` (no `.value`). Only objects/arrays/Map/Set — NOT primitives.
- `computed(() => c.value * 2)` — cached, lazy, read-only by default; writable via `computed({get,set})`. Return is a ref (`.value`).
- `watch(src, (n,o)=>{}, {immediate,deep,flush:'post'})` — `src` = ref / getter `()=>x.a` / array. Objects need `{deep:true}` (or watch a getter of the field). `flush:'post'` runs after DOM.
- `watchEffect(() => {...})` — runs immediately, auto-tracks deps read inside; returns stop fn. `onWatcherCleanup(fn)` / cleanup arg for cancellation.
- `toRef(obj,'k')` / `toRefs(obj)` — keep reactivity when destructuring a reactive object. `unref(x)` = `isRef(x)?x.value:x`. `shallowRef`/`shallowReactive` for perf (top-level only). `readonly(obj)`. `toRaw`, `markRaw`.

## Props / emits / v-model
- `const props = defineProps<{id:number; tags?:string[]}>()` or runtime `defineProps({id:{type:Number,required:true,default:0}})`. Props are readonly; don't mutate.
- Destructuring props keeps reactivity in Vue 3.5+ (compiler-tracked); default via `const { id = 1 } = defineProps()`. Watch a destructured prop with a getter: `watch(() => id, ...)`.
- `const emit = defineEmits<{save:[id:number]}>()` -> `emit('save', 1)`. Parent: `<Child @save="onSave"/>`.
- `v-model` sugar: `<Child v-model="x"/>` <-> child `const m = defineModel()` (Vue 3.4+); `m.value = ...`. Named: `defineModel('title')` <-> `v-model:title`. Legacy: `modelValue` prop + `update:modelValue` emit.

## Template / directives
- `v-if`/`v-else-if`/`v-else` (conditional render), `v-show` (toggles CSS `display`, stays mounted). `v-for="(item,i) in list" :key="item.id"` — always `:key`; never combine `v-if`+`v-for` on same element.
- Binding: `:href`, `:class="{active:isOn}"`/`[a,b]`, `:style`, `v-bind="obj"` spread. Events `@click`, modifiers `@click.stop.prevent`, `@keyup.enter`, `@submit.prevent`. `v-model.number/.trim/.lazy`.
- `<template>` for grouping without wrapper element. `ref="el"` + `const el = useTemplateRef('el')` (3.5) or `const el = ref(null)` matched by name.

## Slots
- Default: parent `<Child>content</Child>` -> child `<slot/>`. Named: `<slot name="header"/>` + parent `<template #header>`. Scoped: child `<slot :row="r"/>` -> parent `<template #default="{row}">`. Fallback: content inside `<slot>fallback</slot>`.

## Lifecycle (Composition)
- `onMounted`, `onBeforeMount`, `onUpdated`, `onBeforeUpdate`, `onUnmounted`, `onBeforeUnmount`, `onErrorCaptured`, `onActivated`/`onDeactivated` (`<KeepAlive>`). Registered synchronously in `setup`. `nextTick(() => {})` awaits DOM flush.

## provide / inject (DI)
- Ancestor `provide('key', value)` (or `provide(keySymbol, ref)`); descendant `const v = inject('key', defaultVal)`. Provide a `ref`/`reactive` for reactivity; provide readonly + an updater fn to keep mutations in the provider. Use `InjectionKey<T>` symbol for typing.

## Pinia (state)
```js
export const useCounter = defineStore('counter', () => {
  const n = ref(0)                     // state
  const dbl = computed(() => n.value*2) // getter
  function inc(){ n.value++ }           // action
  return { n, dbl, inc }
})               // setup store; option store = {state,getters,actions}
```
- Use in component: `const s = useCounter()`; access `s.n`, `s.dbl`, `s.inc()`. Destructure with `const { n } = storeToRefs(s)` to keep reactivity (actions can be plain-destructured). `s.$patch({n:5})` / `s.$reset()` / `s.$subscribe`. Stores are singletons; global replaces Vuex.

## Vue Router
- `createRouter({ history: createWebHistory(), routes:[{path:'/u/:id', component:User, name:'user', children:[...], meta:{auth:true}}] })`.
- In component: `const route = useRoute()` (reactive `route.params.id`, `route.query`), `const router = useRouter()` (`router.push({name:'user',params:{id}})`, `.replace`, `.back`). `<router-link :to>` + `<router-view/>`. Lazy: `component: () => import('./X.vue')`.
- Guards: `router.beforeEach((to,from)=> false|'/login'|true)`; per-route `beforeEnter`; in-component `onBeforeRouteLeave`/`Update`. `<router-view v-slot="{Component}">` + `<KeepAlive>`/`<Transition>`.

## Composables (reusable logic)
- A composable = a function using `use` prefix that calls Composition API and returns reactive state: `function useMouse(){ const x=ref(0); onMounted(()=>window.addEventListener(...)); onUnmounted(...); return {x} }`. Replaces mixins/HOCs. Call at top of `setup` (not inside conditionals/loops — must run synchronously to bind lifecycle/inject).
- Return `ref`s (not raw values) so consumers stay reactive. Compose composables inside composables. Use for shared state (module-level `ref`), fetching (`useFetch` pattern), event listeners, timers.

## Dynamic / async components + built-ins
- `<component :is="tabComponent">` — dynamic component by name/definition. Keep alive tab state: `<KeepAlive><component :is="cur"/></KeepAlive>` (`include`/`max` props; `onActivated`/`onDeactivated` hooks).
- `const Async = defineAsyncComponent(() => import('./Heavy.vue'))` — lazy-load + code-split; options form `{loader, loadingComponent, errorComponent, delay, timeout}`.
- `<Suspense>` — coordinates async `setup`/async components: `<template #default>` + `<template #fallback>`; needed for top-level `await` in `setup`.
- `<Teleport to="body">` — render content elsewhere in DOM (modals, tooltips) while keeping logical parent. `disabled` prop.
- `<Transition>` (single element enter/leave) + `<TransitionGroup>` (list, needs `:key`, animates reorder via FLIP). CSS hook classes `v-enter-from`/`v-enter-active`/`v-leave-to`; JS hooks `@enter`, `@leave`.

## TypeScript + misc
- Typed props/emits via generic macros: `defineProps<Props>()`, `defineEmits<{save:[id:number]}>()`. `PropType<T>` for runtime form. `ref<string[]>([])`, generic components `<script setup lang="ts" generic="T">`.
- `defineExpose({method})` — expose members to `ref` on parent (script-setup is closed by default). `useAttrs()`, `useSlots()`. `inheritAttrs:false` + `v-bind="$attrs"` for fallthrough control.
- Custom directive: `app.directive('focus', { mounted(el){ el.focus() } })` or local `vFocus` in `<script setup>`; hooks `mounted`/`updated`/`beforeUnmount`. Use `<div v-focus>`.
- Global: `const app = createApp(App); app.use(pinia); app.use(router); app.component('X',X); app.provide(k,v); app.config.errorHandler=...; app.mount('#app')`.

## Nuxt 3 (meta-framework)
- File routing `pages/`, `useFetch`/`useAsyncData` (SSR data + dedupe), auto-imports (`ref`, composables, `components/`), `server/api/` routes, `useState` (SSR-safe shared state), `definePageMeta`, layouts, middleware (`defineNuxtRouteMiddleware`), Nitro server, `useRuntimeConfig`, `<NuxtLink>`/`navigateTo`. SSR/SSG/hybrid via `routeRules`. `<ClientOnly>` for browser-only UI.

## Gotchas -> Fix
- Destructuring a `reactive()` object -> loses reactivity (you copied a plain value). -> `const {a} = toRefs(obj)` then use `a.value`, or keep accessing `obj.a`.
- Forgetting `.value` on a `ref` in JS (works in template, breaks in script) -> always `.value` outside template; enable the Volar/ESLint hint. Reassigning `ref` itself (`c = ref(1)`) loses reactivity — set `c.value`.
- `reactive()` on a primitive (`reactive(0)`) -> no reactivity/warns. -> use `ref` for primitives.
- Replacing the whole `reactive` object (`state = {...}`) breaks references. -> mutate properties, or use a `ref` wrapping the object and set `.value`.
- Array/object edits not updating: Vue 3 proxies handle index/length/add/delete fine (unlike Vue 2). But replacing a `shallowRef`/`shallowReactive` nested value won't track -> use deep `reactive`/`ref` or `triggerRef`.
- `watch` on a reactive object doesn't fire on nested change -> pass `{deep:true}` or watch a getter of the exact field.
- Mutating a prop -> Vue warns, parent overwrites on re-render. -> emit an event / `v-model` / local copy via `ref(props.x)` + watch.
- `v-if` + `v-for` on same tag -> `v-if` has higher priority (Vue 3) causing confusion. -> wrap in `<template v-for>` and put `v-if` inside, or filter in a computed.
- Missing/duplicate `:key` in `v-for` -> wrong reordering/state bleed. -> stable unique key (not index if list mutates).
- Losing store reactivity via `const {count} = store` -> use `storeToRefs(store)`.
- Reactivity across module boundary: exporting a `let` and reassigning breaks it -> export a `ref`/`reactive` and mutate `.value`/properties.
- `async setup()` without `<Suspense>` -> component won't render. -> avoid top-level await unless wrapped in `<Suspense>` (or Nuxt).
- Accessing template `ref` in `onMounted` returns null if `v-if`-hidden -> ensure element rendered; refs populate after mount.
- `computed` used to trigger side effects -> getters must be pure. -> use `watch`/`watchEffect` for effects.
- Calling a composable / lifecycle hook conditionally or after `await` in `setup` -> bindings lost/wrong instance. -> call synchronously at top of `setup`.
- `v-html` with user content -> XSS. -> sanitize; prefer text interpolation `{{ }}` (auto-escaped).
- `<TransitionGroup>` items not animating on reorder -> missing unique `:key`; index keys break FLIP.
- Fallthrough attributes landing on the wrong root (multi-root component) -> ambiguous; set `inheritAttrs:false` + explicit `v-bind="$attrs"`.
- Parent can't call child method -> script-setup is closed; child must `defineExpose({fn})`, parent uses template `ref`.
- `watchEffect` fires before you want / can't tell which dep changed -> use `watch` with explicit source(s) for control + old/new values.
