# TypeScript

## Narrowing
- Guards: `typeof x === "string"`, `x instanceof Cls`, `"key" in obj`, `Array.isArray(x)`, truthiness `if (x)`, equality `x === null`.
- Discriminated unions: shared literal `kind` field; `switch` narrows each branch. Exhaustiveness: `default: const _: never = s;` — compile error when a variant is added.
```ts
type Shape = {kind:"circle";r:number} | {kind:"square";s:number};
```
- Custom guard: `function isCat(a: Animal): a is Cat { return "meow" in a }`. Assertion fn: `function assert(x: unknown): asserts x is string`.
- Narrowing is lost across closures/`await` for `let`/mutable props — copy to a `const` first.
- `!` (non-null) has **no runtime check** — prefer a guard or `?? fallback`.

## any / unknown discipline
- `unknown` = safe top type: must narrow before use. `any` disables checking and **infects** everything it touches — quarantine at boundaries.
- Parse external data (`JSON.parse`, `fetch`, env) as `unknown`, validate (zod/manual guards), then use. Never `as MyType` a network payload.
- `catch (e)` is `unknown` under `strict`: `if (e instanceof Error) e.message`.
- `as` casts bypass safety both directions; `x as unknown as T` is a code smell. Prefer `satisfies` (below), guards, or schema validation.

## Generics
- `function pick<T, K extends keyof T>(o: T, k: K): T[K]` — constrain with `extends`, index with `keyof`.
- Default param: `function make<T = string>(): T[]`. Const type param preserves literals: `function f<const T>(x: T)`.
- Inference flows from arguments; pass explicit `<T>` only when inference fails.
- A type param used **once** is usually pointless — take the concrete type.

## Utility Types
- `Partial<T>` / `Required<T>` / `Readonly<T>`; `Pick<T,K>` / `Omit<T,K>`; `Record<K,V>`.
- `ReturnType<F>`, `Parameters<F>`, `InstanceType<C>`, `Awaited<P>` (unwraps nested Promises).
- Union tools: `Exclude<U,X>`, `Extract<U,X>`, `NonNullable<T>`.
- Template literal types: `` type Route = `/${string}` ``; `Uppercase<S>`, `Capitalize<S>`.
- Mapped: `{ [K in keyof T]?: T[K] }`; key remap: `` { [K in keyof T as `get${Capitalize<K & string>}`]: () => T[K] } ``.
- Conditional + infer: `type Elem<T> = T extends (infer U)[] ? U : never`. Conditionals **distribute** over naked union params — wrap `[T] extends [X]` to prevent.

## satisfies & as const
- `satisfies` validates against a type while keeping the narrower inferred type:
```ts
const cfg = { port: 3000, host: "localhost" } satisfies Config; // keys checked, port stays number
```
- `as const`: deep-readonly, no widening. Enum replacement:
```ts
const Color = { Red: "red", Blue: "blue" } as const;
type Color = typeof Color[keyof typeof Color]; // "red" | "blue"
```
- Prefer literal unions / `as const` over `enum` (runtime emit; numeric enums loosely checked; `const enum` breaks under `isolatedModules`).

## keyof / typeof / indexed access
- `keyof T` → union of keys; `typeof val` → type of a value; combine: `keyof typeof obj`.
- Indexed: `T["field"]`, `T[number]` (array element), `T[keyof T]` (all value types).

## interface vs type
- `interface` for object shapes: `extends`, declaration merging, clearer errors. `type` for unions, intersections, tuples, mapped/conditional types, aliases.
- Structural typing: compatibility by shape, not name. Excess-property checks fire only on **fresh object literals** — assigning via a variable skips them.

## tsconfig essentials
- `"strict": true` always. Add: `noUncheckedIndexedAccess` (`arr[i]` becomes `T | undefined`), `exactOptionalPropertyTypes`, `noFallthroughCasesInSwitch`, `noImplicitOverride`.
- Node: `"module": "NodeNext", "moduleResolution": "NodeNext"` — ESM imports then need explicit `.js` extensions (yes, `.js` inside `.ts` source). Bundler (vite/esbuild): `"module": "ESNext", "moduleResolution": "Bundler"`.
- `target` ES2022+; `lib` adds ambient APIs (`"DOM"`, `"ES2023"`). `skipLibCheck: true` to ignore broken dependency types.
- `isolatedModules: true` (required by esbuild/swc): forces `export type { T }` for type-only re-exports. `verbatimModuleSyntax` enforces `import type`.
- `declaration: true` emits `.d.ts` — generate, don't hand-maintain.

## Common tsc errors -> Fix
- **TS2339** "property does not exist" → narrow the union first, or fix the type — don't cast.
- **TS2345/2322** "not assignable" → variance: `string` fits `string | number`, not vice versa; passing `string[]` where `(string|number)[]` will be mutated is unsafe.
- **TS7053** implicit `any` index → type as `Record<string, V>` or guard: `if (k in obj)`.
- **TS2532/18048** "possibly undefined" → `if (x)`, `?.`, `??` — not `!`.
- **TS2742** "cannot be named" in emit → export the intermediate type explicitly.
- **TS2769** "no overload matches" → read the **last** overload's error; one arg is slightly off.
- **ERR_REQUIRE_ESM** → CJS importing ESM-only package: dynamic `import()`, or go full ESM (`"type":"module"` + NodeNext).

## Functions & objects
- Annotate params + returns of **exported** functions; let locals infer (`const n = 5` is `5`; `let` widens).
- Optional `x?: T` ≠ `x: T | undefined` — the latter requires the key present.
- `readonly` inputs: `function sum(xs: readonly number[])` accepts mutable and readonly arrays.
- No typed throws — model expected failures as `{ok:true; value:T} | {ok:false; error:E}` unions.
- Overloads: signatures above one permissive implementation; prefer unions/generics when they suffice.

## Classes & declarations
- `implements I` checks shape but adds nothing; `private` is compile-time only — `#field` is real runtime privacy. Parameter properties: `constructor(private db: Db) {}` declares + assigns.
- `abstract` classes for shared implementation + required overrides; mark overrides with `override` (enforced by `noImplicitOverride`).
- Ambient declarations: `declare global { interface Window { myApp: App } }` in a `.d.ts` or module file with `export {}`. Augment a module: `declare module "lib" { interface Options { extra?: boolean } }`.
- Untyped JS dep → `npm i -D @types/<pkg>`; if none exists, a one-line `declare module "pkg";` unblocks (typed as `any` — wrap it).

## Gotchas -> Fix
- **`any` spreads silently** — one untyped call detypes a module. Fix: boundary-validate to `unknown`; keep `strict` on.
- **`as` cast hides drift** — type changes, cast still compiles. Fix: `satisfies`, guards, schema parse.
- **Narrowing lost after `await`/callback** on mutable bindings. Fix: snapshot to `const`.
- **`Object.keys(o)` is `string[]`**, not `(keyof T)[]` (excess props possible). Fix: cast only for closed objects you own.
- **JSON round-trip lies**: `Date`→`string`, `undefined` fields vanish, `Map`/`Set`→`{}`. Fix: separate wire types from domain types.
- **Distributive conditional surprise**: `T extends X ? A : B` splits unions. Fix: `[T] extends [X]`.
- **Excess-property check skipped via variable**. Fix: `satisfies` on the literal.
- **Method vs property variance**: `m(x: T): void` is bivariant; `m: (x: T) => void` strictly checked. Fix: property-fn syntax for safety-critical callbacks.
- **`tsc` passes, runtime fails** — types erase; nothing validates at runtime. Fix: validate every trust boundary (zod/valibot/guards).
- **`enum` reverse mappings** pollute `Object.keys`/values on numeric enums. Fix: literal unions / `as const` objects.
- **`==` coerces** (`0 == ''` true). Fix: always `===` / `!==`.
