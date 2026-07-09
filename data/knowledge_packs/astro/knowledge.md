# Astro (islands, content, SSR/SSG)

## Model
- **Zero JS by default**: `.astro` components render to static HTML at build (SSG) or request (SSR); no client runtime ships unless you opt an island in. Great for content-heavy/marketing sites.
- **Islands architecture**: interactive UI framework components (React/Vue/Svelte/Solid/Preact) are isolated "islands" hydrated independently; the rest of the page stays static HTML.
- Multi-framework: mix React + Svelte islands on the same page. `.astro` files can't be hydrated (they're template-only); only framework components hydrate.

## `.astro` component
```astro
---
// frontmatter = component script, runs at BUILD/REQUEST time (server only)
import Card from '../components/Card.astro';
import Counter from '../components/Counter.jsx';
const { title } = Astro.props;            // props from parent
const posts = await fetch(url).then(r=>r.json()); // top-level await OK
---
<h1>{title}</h1>
{posts.map(p => <Card post={p} />)}
<Counter client:visible />               <!-- hydrated island -->
<style>h1 { color: red }</style>          <!-- scoped by default -->
```
- Frontmatter (between `---`) runs on the server only — safe for secrets/DB/fs; never ships to client. Everything below is JSX-like template.
- `Astro.props`, `Astro.params` (dynamic routes), `Astro.request`, `Astro.url`, `Astro.redirect()`, `Astro.cookies`, `Astro.slots`. `<slot/>` (+ named `<slot name="x"/>`) for children.
- Styles `<style>` are scoped to the component; `<style is:global>` or `:global()` for global. `class:list={[...]}` helper. `define:vars={{color}}` injects server vars into CSS/scripts.
- `<script>` (plain, no directive) is processed/bundled + runs in browser once, module-scoped — NOT hydration; use for vanilla DOM. `is:inline` to keep raw.

## `client:` hydration directives (on framework islands)
- `client:load` — hydrate immediately on page load (high priority, above-fold interactive).
- `client:idle` — hydrate when browser idle (`requestIdleCallback`); lower priority.
- `client:visible` — hydrate when it scrolls into viewport (`IntersectionObserver`); best for below-fold. `client:visible={{rootMargin:'200px'}}`.
- `client:media="(max-width:600px)"` — hydrate only when media query matches (e.g. mobile menu).
- `client:only="react"` — skip SSR entirely, render only on client (must name the framework). Use for browser-only libs; causes layout shift / no SSR content.
- No directive = static: rendered to HTML, zero JS, non-interactive.

## Routing (file-based, `src/pages/`)
- `src/pages/index.astro` -> `/`; `about.astro` -> `/about`; `blog/[slug].astro` -> dynamic; `[...path].astro` rest. Also `.md`/`.mdx` pages and `.js`/`.ts` endpoints (`export function GET({params}){ return new Response(...) }`).
- Static dynamic routes need `export function getStaticPaths(){ return [{params:{slug:'a'}, props:{...}}] }` (SSG). SSR mode: no getStaticPaths; params resolved per request.

## Content collections (`src/content/` or `src/content.config.ts`)
```ts
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/blog' }),
  schema: z.object({ title: z.string(), date: z.coerce.date(), draft: z.boolean().default(false) }),
});
export const collections = { blog };
```
- Query: `import { getCollection, getEntry, render } from 'astro:content'`; `const posts = await getCollection('blog', p => !p.data.draft)`; `const { Content } = await render(post)` -> `<Content/>`. Zod schema validates frontmatter at build (type-safe). Generate pages via `getStaticPaths` over the collection.

## SSR vs SSG + adapters
- Default = static (SSG): all pages prebuilt to HTML. Per-page override: `export const prerender = false` (make a page SSR) or `true`.
- Add an **adapter** for SSR/on-demand: `@astrojs/node`, `-vercel`, `-cloudflare`, `-netlify`. `output: 'static' | 'server'` in `astro.config.mjs` (v5 uses per-page `prerender` with an adapter). SSR unlocks `Astro.request`, cookies, dynamic responses, API routes.
- Integrations: `integrations: [react(), svelte(), tailwind(), mdx(), sitemap()]` in config; `npx astro add react`.

## View transitions / client router
- `import { ClientRouter } from 'astro:transitions'` in `<head>` -> SPA-like animated nav using the View Transitions API; falls back gracefully. `transition:name="hero"`, `transition:animate="slide"`, `transition:persist` (keep an island/state across navigations). Lifecycle events: `astro:page-load`, `astro:after-swap`.

## Layouts, slots, Markdown/MDX
- No special layout API — a `.astro` component with `<slot/>` used as a wrapper: `layouts/Base.astro` renders `<html><head>...<slot/></html>`; pages `import Base` and wrap content. Named slots for head/footer regions.
- `.md`/`.mdx` pages get a `layout` frontmatter key -> wraps rendered content; MDX allows importing/using components inline. `set:html`/`set:text` directives for raw/escaped injection.

## Endpoints / API routes
- `src/pages/api/x.ts`: `export const GET: APIRoute = ({params, request}) => new Response(JSON.stringify(data), {headers:{'Content-Type':'application/json'}})`. `POST`/`PUT`/etc. Static mode -> GET-only, prerendered; SSR -> full dynamic + `request.formData()`. `export const prerender=false` per endpoint.

## Server islands + actions (v4.15+/v5)
- **Server islands**: `<Avatar server:defer/>` renders a placeholder in the static/cached page, then fetches the component's HTML on demand — mix cacheable static shell with per-request dynamic bits without full SSR.
- **Actions**: `defineAction({ input: z.object({...}), handler: async(input,ctx)=>... })` in `src/actions/`; call type-safely from client (`actions.like(...)`) with validation + progressive-enhancement form support.

## Middleware
- `src/middleware.ts`: `export const onRequest = (context, next) => { context.locals.user = ...; return next() }`. Runs on every request (SSR); set `Astro.locals`, auth, redirects, response rewriting. `sequence(...)` to chain.

## Data / env
- `import.meta.env.PUBLIC_X` exposed to client (needs `PUBLIC_` prefix); non-prefixed are server-only. `Astro.glob()`/`import.meta.glob` for bulk imports. `astro:assets` `<Image src={img} width height alt/>`/`getImage()` for optimized images (built-in Sharp). `astro:env` for typed schema-validated env vars.

## Gotchas -> Fix
- Island shows but "isn't interactive" -> you forgot a `client:*` directive; static by default. Add `client:load`/`visible`.
- State shared between two islands doesn't sync -> each island is a separate root; they don't share React/Vue context. -> lift to nanostores (`@nanostores/react` etc.), custom events, URL, or a single larger island wrapping both.
- `client:visible` component flashes empty / layout shift with `client:only` -> `client:only` has no SSR HTML; reserve space or use `client:visible`/`load` so SSR content exists first.
- Importing a browser-only lib crashes the build (references `window`/`document` in SSR) -> use `client:only="react"`, or guard with `if (typeof window !== 'undefined')`, or move to a `<script>`.
- Passing non-serializable props (functions, class instances) to an island -> props must be JSON-serializable to cross the server->client boundary; pass primitives/plain objects, wire behavior inside the island.
- Frontmatter secret leaking -> it doesn't (server-only), but anything in `<script>` or island props DOES ship. Keep secrets in frontmatter/endpoints only.
- Content collection type/validation error at build -> frontmatter doesn't match the Zod `schema`; fix the field or the schema (use `z.coerce.date()` for date strings).
- Dynamic route 404 in static build -> missing/incorrect `getStaticPaths`; every param combo must be returned. SSR? set `prerender=false` + adapter.
- `<style>` not affecting child component -> styles are scoped; use `:global()`, `is:global`, or pass a class the child applies.
- Plain `<script>` runs once but not per-island / doesn't re-run after view-transition nav -> listen to `astro:page-load` to re-init, or use `data-astro-rerun`.
- Nested `client:load` islands double-hydrate -> don't nest hydrated islands; hydrate the outer one and render children as its own components.
- `import.meta.env.MY_KEY` undefined on client -> add `PUBLIC_` prefix, else it's stripped from the browser bundle.
- `Astro.request.headers`/cookies empty or `.locals` unset -> only populated in SSR (on-demand) routes; a prerendered page has no request. Set `prerender=false` + adapter.
- `server:defer` island shows placeholder forever -> ensure an adapter is configured and the route isn't fully prerendered; server islands need on-demand rendering.
- `getStaticPaths` runs but props are `undefined` in the page -> return `{params, props}` shape; read via `Astro.props`, params via `Astro.params`.
- Middleware not running -> file must be `src/middleware.ts` exporting `onRequest`; only fires for SSR/on-demand routes, not static prerendered output.
- MDX component not rendering -> import it in the MDX file and use JSX; ensure `@astrojs/mdx` integration is added.
- Unoptimized/huge images -> use `astro:assets` `<Image>`/`<Picture>` (or `getImage`) instead of raw `<img>` for build-time optimization.
