# TypeScript Advanced Types

## Conditional & distributive conditionals
- `T extends U ? X : Y`. When `T` is a *naked* type parameter and the input is a union, the conditional distributes over each member: `T extends any ? T[] : never` with `A|B` → `A[] | B[]`.
- Disable distribution by wrapping in a tuple: `[T] extends [U] ? ... : ...`. Essential for "is this union assignable as a whole" checks and for `IsNever`.
- `IsNever<T> = [T] extends [never] ? true : false` — plain `T extends never` is always `never` for `never` input (distributes over empty union → `never`).
- `NonNullable<T> = T extends null | undefined ? never : T` — distribution filters unions member-by-member; `never` members drop out of the result union.

## infer
- `infer` introduces a type variable inside the `extends` clause: `T extends (infer E)[] ? E : never`, `T extends Promise<infer R> ? R : T`, `ReturnType<T> = T extends (...a:any)=>infer R ? R : any`.
- Multiple `infer` in one position of overloaded/union call signatures resolves to the *last* overload for `ReturnType`/`Parameters`. Two `infer` with same name in covariant positions → union; in contravariant positions (params) → intersection.
- `infer extends` constraint (TS 4.7+): `T extends `${infer N extends number}` ? N : never` narrows and coerces the inferred type.

## Mapped types & key remapping
- `{ [K in keyof T]: T[K] }` iterates keys. Modifiers: `readonly`, `?`, and removal `-readonly`, `-?` (e.g. `{ [K in keyof T]-?: T[K] }` strips optionality; `Required` does this).
- Key remapping with `as`: `{ [K in keyof T as NewKey]: ... }`. Filter keys by mapping to `never`: `as K extends `on${string}` ? K : never`. Build getters: `as `get${Capitalize<string & K>}``.
- Homomorphic mapped types (`in keyof T`) preserve modifiers, tuple-ness, and array-ness of `T`; a mapped type over `K in SomeUnion` (not `keyof`) does not. This is why `Partial<[a,b]>` stays a tuple.
- Mapping over a union of keys with the same value type = index signature-ish; use `Record<K, V>`.

## Template literal types
- `` `${A}-${B}` `` produces the cross-product union of `A×B`. Intrinsics: `Uppercase`, `Lowercase`, `Capitalize`, `Uncapitalize`.
- Parse with `infer`: split a path `` `${infer Head}/${infer Rest}` ``, extract route params `` `${string}:${infer P}/${infer Rest}` ``. Combine with recursion for full parsers (e.g. typed `express` routes, `printf`).
- Pattern matching: `` T extends `${number}` `` tests numeric strings; useful for branded numeric-string keys.

## Recursive types & limits
- Recursion depth: instantiation is capped (~50 for type instantiation "excessively deep", ~1000 via internal counters). Tail-recursion elimination (TS 4.5+) applies only when the recursive call is in a tail position of a conditional type accumulator → enables long tuple/string recursion. Accumulate into a tuple param, not `[...Prev, X]` nested in non-tail spot.
- Tuple length as counter: `T['length']` for arithmetic (`BuildTuple<N>` then read length). Deep string parsing risks "Type instantiation is excessively deep and possibly infinite" (`ts2589`).

## Variance
- TS infers variance structurally. Function param positions are contravariant, return positions covariant, `readonly` array covariant, mutable array positions invariant-ish (unsoundly bivariant historically).
- `strictFunctionTypes` makes function-type params contravariant — but **method** syntax (`m(x: T): void`) stays bivariant even under the flag; property-function syntax (`m: (x:T)=>void`) is checked contravariantly. Prefer property syntax for callbacks you want checked soundly.
- Explicit variance annotations (TS 4.7): `interface Box<out T>`, `<in T>`, `<in out T>` — for readability/perf on generic-heavy code; TS validates the annotation matches usage.

## const type params, satisfies
- `function f<const T>(x: T)`: infers the narrowest literal/tuple type (like `as const` at the call site) without callers writing `as const`.
- `satisfies`: checks a value against a type *without widening* the value's inferred type. `const cfg = {...} satisfies Record<string, Color>` keeps exact keys/literal value types for later indexing, while still erroring on bad values. Contrast `: Type` annotation which widens to the annotation.

## Branded / nominal types
- TS is structural; simulate nominal with brands: `type UserId = string & { readonly __brand: 'UserId' }`. Construct via an assertion/factory; brand blocks accidental mixing of `UserId` and `OrderId` even though both are strings.
- Unique-symbol brand for stronger isolation: `declare const b: unique symbol; type USD = number & { [b]: 'USD' }`.

## Discriminated unions & exhaustiveness
- Give each variant a common literal discriminant (`kind`/`type`). `switch (x.kind)` narrows per case. Exhaustiveness: `default: const _:never = x` — a new variant makes assignment to `never` fail at compile time.
- `assertNever(x: never): never { throw new Error() }` in default for runtime + type safety.
- Narrowing needs the discriminant to be a literal type, not `string`; use `as const` or literal unions on the field.

## Type predicates & assertion functions
- User-defined guard: `function isCat(a: Animal): a is Cat`. Narrows in the true branch. `arr.filter((x): x is T => !!x)` to drop nullables with correct type.
- Assertion function: `function assert(c: unknown): asserts c` narrows caller flow after the call (throws otherwise); `function assertIsString(x): asserts x is string`. Must have explicit return-type annotation or TS won't treat it as an assertion.
- `this is T` predicate for class/fluent narrowing.

## Module augmentation & declaration merging
- `declare module 'x' { interface Y { ... } }` merges into existing module types (e.g. augment `express.Request`, `Window`, `process.env`). Interfaces merge; type aliases do not.
- Global augmentation: `declare global { interface Window { myLib: ... } }` inside a module (needs an `export {}` to stay a module). `namespace`+`function`/`class` merge for static-plus-callable shapes.
- Augmenting requires the original to be an `interface`/`namespace`; you cannot merge into a `type` alias or a default export.

## Type-level performance
- Avoid deep conditional/recursive chains and large union cross-products (template literals explode combinatorially: `${A}${B}${C}` with big unions can hit millions of members → slow/`ts2590`).
- Prefer interfaces over large intersection types (interfaces cache better). Break giant unions; use `type` aliases named so errors are readable. `--generateTrace`/`--extendedDiagnostics` to find hot spots; watch "instantiation count".

## Common tsc errors decoded
- `ts2589` "excessively deep and possibly infinite" → recursion/union blowup → add a depth cap or refactor to tail recursion.
- `ts2322` assignability → structural mismatch; read expected vs actual; often excess-property or variance.
- `ts2345` argument not assignable → param variance / literal-widening.
- `ts2536` `K cannot be used to index T` → key not proven `keyof T`; constrain `K extends keyof T`.
- `ts2536`/index errors on mapped output → missing key remap constraint.
- "Type is referenced directly or indirectly in its own base expression" → circular type; break the cycle with an interface or lazy indirection.

## Gotchas -> Fix
- Conditional distributing when you wanted whole-union check → **wrap both sides in 1-tuples `[T] extends [U]`**.
- `T extends never` never true for `never` input → **use `[T] extends [never]`**.
- `satisfies` vs `:` confusion: annotation widens keys/values, losing literal inference for later indexing → **use `satisfies` to validate while preserving the literal type**.
- Method-syntax callback types silently accept unsound args under `strictFunctionTypes` → **declare callbacks as property function types**.
- Branded type "accepts a plain string" → you annotated a return but never enforced construction → **only mint brands through a factory/assertion; never cast raw inputs blindly**.
- Exhaustive `switch` compiles even after adding a variant → you forgot the `never` default → **add `default: assertNever(x)`**.
- Guard `x is T` returns boolean but doesn't narrow in `.filter` → arrow lacks the predicate annotation → **annotate `(x): x is T =>`**.
- Assertion function doesn't narrow → missing explicit `asserts` return annotation (inference can't add it) → **write the full `asserts x is T` signature**.
- Module augmentation silently ignored → file isn't a module, or you targeted a `type`/default export → **add `export {}`; augment the `interface`/`namespace`**.
- Homomorphic mapped type unexpectedly loses tuple-ness → you mapped `K in Union` not `K in keyof T` → **map over `keyof T`**.
- `keyof T` on union `T` yields only common keys → **use a distributive helper or `T extends any ? keyof T : never`**.
- Template literal type compiles slowly / `ts2590` → union cross-product explosion → **shrink unions; avoid multi-slot templates over large unions**.
- `Partial`/`Readonly` "not deep" surprises → they're one level → **write a recursive `DeepPartial` with tail-safe recursion**.
- Index access `T[K]` widened to `any` under `noUncheckedIndexedAccess` off → out-of-range reads unchecked → **enable the flag; expect `T | undefined`**.
