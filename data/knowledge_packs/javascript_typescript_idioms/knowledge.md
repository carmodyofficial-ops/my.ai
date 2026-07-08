# JavaScript / TypeScript Idioms

## Modern syntax you should reach for first
- `const` by default, `let` if reassigned, never `var` (function-scoped, hoisted, loop-closure bugs).
- Optional chaining short-circuits on `null`/`undefined`: `a?.b?.()?.[i]`. Pair with nullish coalescing: `port ?? 3000`.
- **`??` vs `||`**: `||` wrongly replaces `0`, `''`, `false`; `??` only replaces null/undefined. Assignment forms: `x ??= v`, `x ||= v`, `x &&= v`.
- Destructure with defaults + rename + rest: `const {a, b: alias = 1, ...rest} = obj`; arrays: `const [x, , z] = arr`; swap: `[a, b] = [b, a]`. Defaults fire only on `undefined`, **not** `null`/`0`.
- Spread to copy, never mutate shared: `{...o, k: v}`, `[...a, x]` — **shallow** copy; deep: `structuredClone(o)` (handles Date/Map/Set; not functions).
- Template literals `` `${x}` ``; tagged templates for escaping/DSLs.
- `Object.entries(o)` / `Object.fromEntries(pairs)` for object↔pairs transforms; `Object.groupBy(items, fn)` / `Map.groupBy` (ES2024).

## Arrays over loops
- `map`/`filter`/`find`/`findLast`/`some`/`every`/`flatMap`/`reduce`; `at(-1)` for last element; `includes` for membership.
- Non-mutating variants (ES2023): `toSorted`, `toReversed`, `toSpliced`, `with(i, v)` — `sort`/`reverse`/`splice` mutate in place.
- Numeric sort needs a comparator: `arr.sort((a,b)=>a-b)` — default sorts **lexicographically** (`[10,2,1]` → `[1,10,2]`).
- `for...of` iterates values (works on any iterable); `for...in` iterates keys incl. inherited — never for arrays.
- Build sequences: `Array.from({length: n}, (_, i) => i)`; dedupe: `[...new Set(arr)]`.
- Use `Map` for non-string keys / frequent add-delete; `Set` for membership. Plain objects inherit prototype keys — `Object.create(null)` or `Map` for user-keyed dicts.

## Promises & async patterns
- Parallel: `await Promise.all([f(), g()])` — awaiting inside a loop serializes. Tolerate failures: `Promise.allSettled`; first success: `Promise.any`; race/timeout: `Promise.race([p, timeout(5000)])` or `AbortSignal.timeout(5000)` with `fetch`.
- **`Promise.all` fails fast** — one rejection rejects the whole thing (others keep running, unobserved).
- Every promise needs `await` or `.catch` — floating promises swallow errors and crash Node on rejection.
- `async` functions always return a promise; `throw` inside → rejected promise; `try/catch` around `await` catches rejections.
- `for await (const chunk of stream)` for async iterables. Concurrency-limit big fan-outs (p-limit pattern) instead of `Promise.all` on 10k items.
- Don't mix `.then` chains with `await` in one function. Inside `try/catch`, use `return await p` (bare `return p` escapes the catch — the rejection is never caught there); outside try, bare `return p` is fine.

## Equality & coercion gotchas
- `===`/`!==` always. `==` coerces: `0 == ''`, `'' == false`, `null == undefined` are all true.
- `typeof null === 'object'` — test `v === null`. `typeof f === 'function'`; `Array.isArray(a)` (typeof array is `'object'`).
- `NaN !== NaN` — use `Number.isNaN(x)` (global `isNaN` coerces first). `Object.is(-0, +0)` is false.
- `0.1 + 0.2 !== 0.3` — floats: compare with epsilon or compute in integer cents/`BigInt`.
- `+` concatenates when either side is a string: `1 + '2' === '12'`; `'3' - 1 === 2`. Convert explicitly: `Number(s)`, `String(n)`.
- Falsy set is exactly: `false, 0, -0, 0n, '', null, undefined, NaN`. Empty `[]` and `{}` are **truthy**.
- Objects/arrays compare by reference: `[1] !== [1]` — deep-compare explicitly or compare serialized keys.

## this-binding
- Arrow functions capture lexical `this` (and have no `arguments`); regular functions get `this` from the **call site**.
- Object methods needing dynamic `this`: `method() {}` shorthand, not arrows. Extracted method loses `this`: `const f = obj.m; f()` → undefined `this`. Fix: `obj.m.bind(obj)` or `() => obj.m()`.
- Class handlers for events/callbacks: class field arrow `handle = () => {...}` or bind in constructor.
- `call`/`apply` set `this` per call; `bind` returns a permanently bound copy.

## Event loop essentials
- One thread: run-to-completion per task. Microtasks (promise callbacks, `queueMicrotask`) drain **completely** after each task, before rendering/next task; macrotasks (`setTimeout`, I/O) queue behind.
- Order: sync code → all microtasks → next macrotask. `await` yields to the microtask queue; `setTimeout(fn, 0)` runs later than a resolved promise's `.then`.
- Blocking sync code freezes timers, I/O callbacks, and UI — chunk CPU work or move it off-thread (workers).
- A tight microtask loop (promise that re-queues itself) can starve rendering — use `setTimeout` to yield genuinely.

## Iterators & generators
- Anything with `[Symbol.iterator]` works in `for...of`, spread, destructuring: arrays, strings, `Map`, `Set`, `NodeList` — but **not plain objects** (spread `{...o}` uses own enumerable props, not iteration).
- Generators produce lazy sequences: `function* range(n){ for(let i=0;i<n;i++) yield i }`; consume with `for...of` or `[...range(5)]`. `yield*` delegates to another iterable.
- Async generators (`async function*` + `for await`) model paginated APIs cleanly: yield page items, fetch next inside the loop — the consumer never sees cursors.
- Iterators are single-pass: a consumed generator is empty on the second `for...of` — recreate or cache to an array.

## Modules & misc
- ESM: `export const x` / `export default` / `import {x} from './m.js'`. Imports hoist and are live bindings; circular imports give partially-initialized modules — restructure.
- Dynamic import for lazy load: `const m = await import('./heavy.js')`.
- `JSON.parse` throws on bad input — wrap in `try/catch`. `JSON.stringify` drops `undefined`/functions and throws on circular refs.
- Labeled numeric literals: `1_000_000`. `BigInt` (`10n`) doesn't mix with `number` in arithmetic.
- Getters/setters, computed keys `{[k]: v}`, shorthand `{a, b}`.

## Gotchas -> Fix
- **`var` in loop + closure** captures one shared variable → `let` (fresh binding per iteration).
- **Mutating shared state** (`push`, `sort`, object assignment) causes spooky action → spread copies, `toSorted`, immutable updates.
- **`forEach` with async callback** doesn't await anything → `for...of` + `await`, or `Promise.all(arr.map(async ...))`.
- **`parseInt('08')` legacy radix / `parseInt('12px') === 12`** → `Number(s)` for strict, or `parseInt(s, 10)` when trailing garbage is intended.
- **Array holes** `[1,,3]`: `map` skips them → `Array.from({length:n})`.
- **`sort()` mutates and sorts as strings** → `toSorted((a,b)=>a-b)`.
- **Losing `this` when passing a method as callback** → bind or arrow-wrap.
- **`delete obj.k` in hot paths** deoptimizes → set to `undefined` or use `Map`.
- **Date pitfalls**: months are 0-indexed (`new Date(2026, 0, 15)` = Jan); `Date` parsing of non-ISO strings is implementation-defined → ISO 8601 strings only, or a date library.
- **String replace replaces first match only** → `replaceAll` or `/g` regex.
- **Floating promise in event handler** crashes silently → wrap handler bodies in try/catch or a `safeAsync` helper.
