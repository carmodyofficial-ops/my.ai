# JavaScript / TypeScript Idioms & Gotchas

## Variables & Functions
- `const` by default, `let` if reassigned, never `var` (function-scoped, hoists).
- Arrow fns capture lexical `this`: `arr.map(x => this.f(x))`. Object methods needing `this` must be `method(){}`, not arrows.
- Rebind: `el.addEventListener('click', this.h.bind(this))` or arrow class field `h = () => {}`.

## Destructuring / Spread
- `const {a, b = 1, ...rest} = obj`; `const [x, , z] = arr`.
- Clone, don't mutate shared: `const next = {...o, k: v}`, `[...a, x]`.
- Default only fires on `undefined`, not `null`/`0`.

## Nullish & Optional
- `a?.b?.()?.[i]` short-circuits on null/undefined.
- `??` only for null/undefined: `port ?? 3000`. `||` wrongly replaces `0`/`''`/`false`.

## Arrays over loops
- `map/filter/find/some/every/reduce` instead of index loops. `find` returns item, `findIndex` the index.
- `for...of` iterates values; `for...in` iterates keys (incl. inherited) — never for arrays.

## Async
- `await Promise.all([f(), g()])` for parallel; awaiting in a loop serializes.
- Always `await` or `.catch` — a floating promise swallows errors.
- `for await (const x of stream)` for async iterables.

## Modules
- `export const x`, `export default`, `import {x} from './m.js'`. No side-effect imports unless intended.

## TypeScript
- Enable `strict`. `interface` for object shapes/extension; `type` for unions/aliases: `type Status = 'on'|'off'`.
- Prefer `unknown` over `any`; narrow before use: `if (typeof v === 'string')`.
- Type guards: `function isCat(a): a is Cat { return 'meow' in a }`.
- `as const` freezes literals: `const R = ['a'] as const`. Generics: `function id<T>(x: T): T`.
- `x?: number` allows missing; `x: number | undefined` requires the key.

## Footguns + fixes
- `===` always; `==` coerces (`0 == ''` is true).
- `0.1 + 0.2 !== 0.3` — compare with epsilon or use integers/cents.
- `typeof null === 'object'` — test `v === null` explicitly.
- `NaN !== NaN` — use `Number.isNaN(x)`, not `x === NaN`.
- `JSON.parse` throws — wrap in `try/catch`.
- `[1,,3]` holes: `map` skips them; use `Array.from({length:n})`.
- Sort numbers: `arr.sort((a,b)=>a-b)` (default is lexicographic).
