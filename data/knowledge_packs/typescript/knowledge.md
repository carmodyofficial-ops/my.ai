# TypeScript Reference

## Basic Types
- Primitives: `string`, `number`, `boolean`, `bigint`, `symbol`. Arrays: `T[]` or `Array<T>`.
- Tuple: `[string, number]`; named `[x: number, y: number]`.
- `any` — opts out of checking (avoid). `unknown` — safe top type; must narrow before use. `never` — no value (unreachable/exhaustiveness). `void` — no return value.
- Literal types: `let x: "a" | "b"`; combine with unions for closed sets.

## Annotations & Inference
- Let TS infer locals: `const n = 5` is `5`. Annotate **function params, return types, and public/exported API** for stable contracts.
- `const` infers literal types; `let` widens to base type.

## interface vs type
- `interface` for object shapes; supports `extends` and declaration merging. Prefer for public object/class contracts.
- `type` for unions, intersections, tuples, primitives, mapped/conditional types. `type ID = string | number`.
- Both express objects; pick `interface` for extendable shapes.

## Union & Intersection
- Union `A | B`: either; access only common members until narrowed.
- Intersection `A & B`: has all members of both (merge object types).

## Narrowing
- `typeof x === "string"`, `x instanceof Cls`, `"key" in obj`, truthiness (`if (x)`).
- Discriminated unions: shared literal `kind` field.
```ts
type Shape = {kind:"circle";r:number} | {kind:"square";s:number};
function area(s: Shape){
  switch(s.kind){
    case "circle": return Math.PI*s.r**2;
    case "square": return s.s**2;
    default: const _: never = s; return _; // exhaustive
  }
}
```
- Custom guard: `function isCat(a:Animal): a is Cat {...}`.

## Generics
```ts
function id<T>(x: T): T { return x; }
function longest<T extends {length:number}>(a:T,b:T){...} // constraint
function make<T = string>(): T[] { return []; } // default
```

## Utility Types
- `Partial<T>`, `Required<T>`, `Readonly<T>`.
- `Pick<T,K>`, `Omit<T,K>`, `Record<K,V>`.
- `ReturnType<F>`, `Parameters<F>`, `Awaited<P>` (unwrap Promise).

## keyof / typeof / Indexed / Mapped / as const
- `keyof T` -> union of keys. `typeof val` -> type of a value.
- Indexed access: `T["field"]`, `T[number]` (array element).
- `as const`: deep-readonly literal; freezes values/widening.
- Mapped: `type Opt<T> = { [K in keyof T]?: T[K] }`.

## Enums (prefer alternatives)
- Prefer union of literals or `as const` object:
```ts
const Color = {Red:"red",Blue:"blue"} as const;
type Color = typeof Color[keyof typeof Color];
```
- `enum` emits runtime code; numeric enums are loosely checked.

## tsconfig
- `"strict": true` always. Set `target` (e.g. ES2022), `module`.
- `noUncheckedIndexedAccess: true` — makes `arr[i]` `T | undefined`.

## .d.ts & Structural Typing
- `.d.ts`: ambient type declarations, no emit; describe JS libs / globals.
- TypeScript is structural (duck-typed): compatible if shape matches, regardless of declared name.

## Gotchas -> Fix
- `any` disables checking -> use `unknown` + narrow.
- Non-null `!` hides real nullish bugs -> narrow/guard instead.
- `as` cast bypasses safety (no runtime check) -> validate or use guards.
- `enum` runtime cost + reverse-mapping pitfalls -> union/`as const`.
- `==` does coercion -> always `===` / `!==`.
- Index access may be `undefined` (with `noUncheckedIndexedAccess`) -> check before use.
