# Web Build Tooling

## Bundler internals — models + tradeoffs
- **esbuild** (Go): extreme speed via parallelism + no intermediate GC pressure; single-pass, minimal plugin API, weaker tree-shaking/code-splitting than Rollup, no first-class type-checking (strips types only). Used as Vite's dep pre-bundler + fast transpile.
- **Rollup** (JS): best-in-class ESM tree-shaking + clean library output; slower; rich plugin ecosystem. Vite's *production* bundler.
- **Vite**: dev = native-ESM unbundled (esbuild pre-bundle deps) → instant cold start + granular HMR; prod = Rollup bundle. Dev/prod use different engines → possible behavior gaps.
- **webpack**: most mature/flexible (loaders + plugins, Module Federation, any asset graph); slowest, complex config; persistent filesystem cache mitigates rebuilds.
- **Turbopack** (Rust, Next): incremental function-level caching (Turbo engine), lazy bundling of only requested modules; aims webpack-feature-parity with esbuild-class speed; still stabilizing.
- **rspack** (Rust): webpack-API-compatible, much faster; drop-in for webpack configs/MF.

## Tree-shaking
- Requires **static ESM** (`import`/`export`) — CJS `require` is dynamic, not shakeable; a single CJS dep in the graph can defeat shaking for that subtree.
- **`sideEffects`** in package.json: `false` = whole package is pure, unused exports droppable; array = files with side effects to preserve (CSS imports, polyfills). Missing/incorrect `sideEffects:false` on a lib → dead code retained.
- **`/*#__PURE__*/`** annotations mark a call as side-effect-free so its result, if unused, is removed (critical for factory/IIFE patterns). Minifiers (Terser/esbuild) honor them.
- **Breaks tree-shaking**: re-export barrels (`index.ts` re-exporting everything) pulling whole modules; property access on namespace imports the bundler can't statically resolve; top-level side effects (logging, registration, mutating prototypes); `import * as X` then dynamic key; Babel/tsc transpiling ESM→CJS *before* the bundler (set `"module":"esnext"`/`"preserveModules"`, let bundler handle modules).

## Code splitting
- **Dynamic `import()`** → separate async chunk, loaded on demand (route-level splitting is the big win). Webpack magic comments `/* webpackChunkName: "x" */`, `/* webpackPrefetch: true */`.
- **Vendor chunk**: split stable node_modules from app code for long-term caching; but over-splitting → many requests + duplicated shared deps. Rollup `manualChunks`/`output.manualChunks` function to group.
- **Chunk strategy**: route-based (per lazy route) + a shared "commons" chunk for modules used by ≥N routes; content-hash filenames (`[contenthash]`) for immutable caching; keep vendor hash stable so app changes don't bust it. Watch chunk waterfalls (chunk A imports B imports C serially) — flatten or preload.
- **Preload/prefetch**: `<link rel="modulepreload">` for critical chunks; prefetch idle-time for likely-next routes.

## Module resolution
- **ESM/CJS interop**: `import cjs from 'pkg'` maps to `module.exports` as default; named imports from CJS are synthesized by the bundler (not guaranteed at runtime in native Node ESM — `import { x }` from a CJS pkg can fail). `__esModule` marker + interop helpers (`_interopRequireDefault`) reconcile.
- **`exports` map / conditions**: `"exports": { ".": { "import": "./esm.js", "require": "./cjs.js", "types": "./x.d.ts", "browser": "...", "default": "..." } }`. Conditions resolved in order; `types` must come first for TS; `default` last as fallback. `exports` **blocks deep imports** not listed → `Cannot find module 'pkg/internal'`.
- **Dual-package hazard**: package shipped as both ESM + CJS → bundler loads *both* copies (import path gets ESM, a transitive require gets CJS) → two module instances, duplicated state (e.g. two singletons, `instanceof` fails, separate React contexts). Mitigate: single source of truth (state in a shared CJS core, thin ESM wrapper), or ship ESM-only, or dedupe via bundler resolve.
- Node condition `"node"` vs `"browser"` vs custom (`"development"`); Vite/webpack `resolve.conditions`. `mainFields`/`browser` field legacy fallbacks.

## Source maps
- Types: `source-map` (full, separate file), `inline-source-map` (base64 in bundle — bloats), `hidden-source-map` (generated, no `//# sourceMappingURL` comment → upload to error tracker only), `eval-source-map`/`cheap-module-source-map` (dev speed/accuracy tradeoffs).
- **Security**: production source maps expose original source; use `hidden-source-map` and upload privately to Sentry/etc, don't serve `.map` publicly, or restrict access. Leaked maps = full source disclosure.

## Transpilation
- **SWC** (Rust) / **esbuild**: fast transpile, no type-checking. **Babel**: plugin ecosystem, precise polyfilling. **tsc**: type-check + emit (slow) — typically type-check with `tsc --noEmit` and transpile with SWC/esbuild for speed.
- **Targets / browserslist**: `browserslist` (`.browserslistrc` or package.json) drives which syntax is downleveled + which `core-js` polyfills (`@babel/preset-env` with `useBuiltIns:'usage'`). Over-broad targets (`> 0.5%`) → larger output + more polyfills; set realistic baseline. `esbuild target` / `tsconfig target` separately control syntax level — keep aligned.

## Monorepo builds + caching
- Content-hash task caching (Turborepo/Nx) + declared inputs/outputs; remote cache shares across CI/devs; affected-graph builds only changed subtree; TS project references (`composite`, `--build`) for incremental type-check. Undeclared inputs → cache poisoning.

## Bundle analysis + budgets
- `rollup-plugin-visualizer` / `webpack-bundle-analyzer` / `vite-bundle-visualizer` for treemaps; `source-map-explorer` maps bytes→source. `size-limit`/`bundlesize` as CI gate (fail on regression). Track initial JS, per-route chunk, third-party weight, duplicate deps (`npm ls`/`why`).

## Gotchas -> Fix
- **Dual-package hazard**: two instances of a lib → duplicated singleton/context, `instanceof` false -> dedupe in resolve, ship ESM-only, or centralize state in one format.
- **Tree-shaking dead** because a build step transpiled ESM→CJS first -> keep `module:esnext`, let the bundler see ESM; `sideEffects:false` on pure libs.
- **Barrel `index.ts`** re-exports pull entire modules into every consumer -> import from deep specific paths or mark side-effect-free; consider `no-barrel` lint.
- **`exports` map added** breaks previously-working deep import -> add the subpath to `exports` or import the public entry.
- **Named import from a CJS dep** works in bundler, fails in native Node ESM -> import default then destructure, or use the pkg's ESM entry.
- **Production `.map` served publicly** → source leak -> `hidden-source-map`, upload to error tracker, block public access.
- **Over-splitting vendor** → request waterfall + duplicated shared chunks -> group with `manualChunks`, keep vendor hash stable.
- **`sideEffects:false` too aggressive** drops needed CSS/polyfill imports -> list them in the `sideEffects` array (e.g. `["*.css"]`).
- **browserslist too broad** → bloated polyfilled bundle -> set realistic baseline; audit `preset-env` debug output.
- **Vite dev works, prod breaks** (esbuild dev vs Rollup prod, or a CJS dep needing `optimizeDeps.include`) -> reproduce with `vite build && preview`; add to `optimizeDeps`.
- **`/*#__PURE__*/` stripped** by a transform → previously-removed factory calls now retained -> ensure minifier runs after and annotations survive transpile.
- **Cache false hit** (Turbo/Nx) from undeclared env/tool version -> declare all inputs; a "clean build fixes it" symptom = cache poisoning.
- **`import()` inside a loop with a variable path** → bundler emits every possible chunk or none -> use static-analyzable dynamic imports or explicit glob (`import.meta.glob`).
