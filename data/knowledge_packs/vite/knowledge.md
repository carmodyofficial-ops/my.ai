# Vite Reference

## What it is
Dev server serves source over **native ESM** (no bundling) = instant cold start + fast HMR. Production `build` bundles with **Rollup**. Dep pre-bundling uses **esbuild**.

## Scaffold & scripts
```bash
npm create vite@latest my-app   # pick framework/template
cd my-app && npm install
```
- `npm run dev` — start dev server (HMR)
- `npm run build` — Rollup build -> `dist/`
- `npm run preview` — serve built `dist/` locally (not for prod)

## Layout
- `index.html` — **entry point, at project ROOT** (not in `public/`). Vite resolves `<script type="module" src="/src/main.js">`.
- `src/main.js` — app code; `public/` — static files.

## vite.config.js
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': '/src' } },
  server: { port: 5173, proxy: { '/api': 'http://localhost:3000' } },
  build: { outDir: 'dist' },
  base: '/',          // set to '/subpath/' for non-root deploy
})
```

## Plugins
Framework: `@vitejs/plugin-react`, `@vitejs/plugin-vue`. Rich Rollup-compatible ecosystem; add to `plugins:[]`.

## Env vars
- Only **`VITE_`-prefixed** vars are exposed to client: `import.meta.env.VITE_API_URL`. Others stay server-only (security).
- Defined in `.env`, `.env.local`, `.env.[mode]`.
- Built-ins: `import.meta.env.MODE`, `.DEV`, `.PROD`, `.BASE_URL`.

## Static assets
- `public/` — copied as-is, served at root (`/logo.svg`); no hashing/processing.
- `src/assets` — `import img from './x.png'` -> resolved, hashed URL.
- `import url from './f.png?url'` (URL string), `?raw` (file contents as string).

## Dep pre-bundling
esbuild converts CJS->ESM and bundles deps once; cached in `node_modules/.vite`. Force include via `optimizeDeps.include`.

## Gotchas -> fixes
- **Env var undefined** -> missing `VITE_` prefix (or restart dev server).
- **App blank / scripts not loading** -> `index.html` must be at project root.
- **Weird dep/import errors after install** -> delete `node_modules/.vite` (or `vite --force`).
- **CommonJS dep fails** -> add to `optimizeDeps.include`.
- **404 assets on deploy** -> wrong `base`; set `base:'/repo/'` for subpath hosting.
- **`preview` differs from prod** -> it's only a static preview, not the real server.
