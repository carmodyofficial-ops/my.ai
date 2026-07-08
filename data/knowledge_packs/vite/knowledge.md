# Vite

## Model
- Dev server serves source over **native ESM** (no bundling) = instant cold start + fast HMR. Production `vite build` bundles with **Rollup**. Dependency pre-bundling uses **esbuild**, cached in `node_modules/.vite`.
- `index.html` is the **entry point and lives at project ROOT** (not `public/`): `<script type="module" src="/src/main.ts">`.
- Scripts: `vite`/`npm run dev` (HMR dev server), `vite build` -> `dist/`, `vite preview` (serves built dist locally — a static check, NOT a prod server).
- Scaffold: `npm create vite@latest my-app` (pick template: react-ts, vue, svelte, vanilla...).

## vite.config.ts — the parts you actually touch
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:3000', changeOrigin: true,
                       rewrite: p => p.replace(/^\/api/, '') } },
  },
  base: '/',              // '/repo/' for subpath deploys (GitHub Pages)
  build: { outDir: 'dist', sourcemap: true },
})
```
- Alias must be mirrored in `tsconfig.json` `paths` (`"@/*": ["./src/*"]`) or the editor/tsc disagrees with Vite.
- `proxy` is **dev-only** — production needs a real reverse proxy or absolute API URLs.
- Conditional config: `defineConfig(({ command, mode }) => ({...}))` — `command` is `'serve'` or `'build'`.

## Env vars
- Only **`VITE_`-prefixed** vars reach client code: `import.meta.env.VITE_API_URL`. Unprefixed stay out (secret safety). Change prefix via `envPrefix`.
- Files: `.env` < `.env.local` < `.env.[mode]` < `.env.[mode].local` (mode wins; `.local` is gitignored by convention). Mode: `vite build --mode staging`.
- Built-ins: `import.meta.env.MODE`, `.DEV`, `.PROD`, `.BASE_URL`, `.SSR`.
- Values are **statically replaced at build time** — strings only; not live at runtime. `typeof process` is undefined in client code (use `define` to shim if a dep needs it).
- Restart the dev server after editing `.env` files.

## Assets
- `public/` — copied verbatim to dist root, referenced as `/logo.svg`; no hashing, no import.
- Imported assets: `import img from './x.png'` -> hashed URL (cache-busting). Suffixes: `?url` (URL string), `?raw` (contents as string), `?inline` (data URI).
- `new URL('./img.png', import.meta.url).href` for dynamic asset URLs that Vite can still rewrite.

## Glob imports
- `const mods = import.meta.glob('./pages/*.tsx')` -> map of path -> lazy `() => import(...)`. `{ eager: true }` for immediate imports; `{ as: 'raw' }` / `query: '?url'` variants.
- Pattern must be a **literal string** starting with `./`, `../`, or an alias — no variables.

## Library mode
```ts
build: {
  lib: { entry: 'src/index.ts', name: 'MyLib', fileName: 'my-lib' },
  rollupOptions: { external: ['react', 'react-dom'],
    output: { globals: { react: 'React' } } },
}
```
- Externalize peer deps or you bundle React into the lib. Emit types separately (`vite-plugin-dts` or `tsc --emitDeclarationOnly`).

## Plugins
- Rollup-compatible + Vite-specific hooks. Framework plugins: `@vitejs/plugin-react`, `-vue`, `@sveltejs/vite-plugin-svelte`. Order matters occasionally: `enforce: 'pre' | 'post'`; scope with `apply: 'build' | 'serve'`.
- Minimal custom plugin: `{ name: 'x', transform(code, id) { if (id.endsWith('.foo')) return { code: compile(code) } } }`.

## HMR
- Framework plugins wire component HMR automatically (React Fast Refresh preserves hook state — but editing a file whose exports aren't only components forces a full reload; keep components in their own files).
- Manual API: `if (import.meta.hot) { import.meta.hot.accept(newMod => {...}) }`; state across reloads via `import.meta.hot.data`. Module-level side effects re-run on every hot update — guard them.

## Build tuning & narrower features
- Chunk splitting: `build.rollupOptions.output.manualChunks: { vendor: ['react','react-dom'] }` (or a function) to stabilize caching; the "chunks larger than 500 kB" warning is a hint to code-split via dynamic `import()`.
- Analyze bundle: `rollup-plugin-visualizer`. Disable minify to debug output: `build.minify:false`.
- Multi-page apps: multiple HTML entries via `build.rollupOptions.input: { main: 'index.html', admin: 'admin/index.html' }`.
- Web workers: `new Worker(new URL('./w.ts', import.meta.url), { type: 'module' })` — bundled correctly; `?worker` import also works.
- SSR: `vite dev` middleware mode + `ssrLoadModule` for custom servers, but frameworks (SvelteKit, Nuxt, Astro, React Router/Remix) wrap this — prefer them. `ssr.noExternal` forces bundling of deps that ship untranspiled ESM/CSS.
- Vitest reuses `vite.config` (resolve/aliases/plugins) — one config for app + tests; test-specific bits under `test: {}`.
- TS: Vite transpiles types away per-file (esbuild) and does **no type-checking** — run `tsc --noEmit` (or `vue-tsc`) in CI; `isolatedModules` semantics apply (use `export type`).

## Gotchas -> Fix
- **`import.meta.env.VITE_X` undefined**: missing `VITE_` prefix, wrong `.env` file for the mode, or dev server not restarted.
- **Blank page / no script runs**: `index.html` not at project root, or script tag missing `type="module"`.
- **Weird dep/import errors after installing or linking a package**: stale pre-bundle cache — delete `node_modules/.vite` or run `vite --force`.
- **CJS dep breaks in dev** (`require is not defined`, named-export errors): add it to `optimizeDeps.include`; if it fails at build, `build.commonjsOptions` or ssr `noExternal`.
- **404 assets / broken routes after deploy**: wrong `base` — set `base: '/repo-name/'` for subpath hosting; for SPA history routing, configure host fallback to `index.html`.
- **`process is not defined`**: client code or a dep expects Node globals — use `import.meta.env`, or `define: { 'process.env': {} }`.
- **Dev proxy works, prod 404s on `/api`**: `server.proxy` doesn't exist in prod — deploy a reverse proxy or use full URLs from env.
- **Dynamic import with variable path fails**: bundler needs static analysis — use `import.meta.glob` and pick from the map.
- **`global is not defined`** (Node-oriented libs): `define: { global: 'globalThis' }`.
- **Big-int / modern syntax errors on old browsers**: default target is Baseline modern browsers — use `@vitejs/plugin-legacy` for legacy support, or set `build.target`.
- **HMR updates but page state resets constantly**: mixed exports in component files (Fast Refresh bailout) or a module-scope side effect — isolate components, guard effects with `import.meta.hot.data`.
- **HMR not firing at all in Docker/WSL/VM**: file watching needs polling — `server.watch: { usePolling: true }`; also expose with `server.host: true`.
- **Slow cold start / huge dep scan**: barrel-file imports pull entire libs — import from subpaths; check `optimizeDeps.entries`.
- **`vite preview` differs from prod**: it only serves static files — no SSR, no server middleware; parity-test on the real host.
