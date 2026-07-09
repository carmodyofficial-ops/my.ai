# Frontend Architecture at Scale

## Rendering strategy — decision criteria
- **CSR** (client renders from empty shell): app behind auth, highly interactive, SEO irrelevant. Cost: slow FCP/LCP, big JS, waterfall to data. Ship only when TTI dominated by interaction not first paint.
- **SSG** (build-time HTML): content stable between deploys (docs, marketing, blog). Fastest TTFB (CDN static). Fails when content count huge (build time blows up) or personalization needed.
- **ISR** (stale-while-revalidate at edge, Next `revalidate`): SSG economics + periodic freshness. Watch the *first* request after invalidation serves stale; on-demand revalidation (`revalidateTag`/`revalidatePath`) for precise busting.
- **SSR** (per-request HTML): personalized + SEO + fresh. Cost: server compute per request, TTFB tied to data latency, hydration cost. Cache with `Vary`/CDN keys carefully.
- **Streaming SSR** (React `renderToPipeableStream`, `<Suspense>`): flush shell immediately, stream slow chunks. Improves TTFB/LCP without blocking on slowest query. Requires HTTP streaming through every proxy (buffering reverse proxies kill it).
- **Islands** (Astro, Qwik): mostly-static HTML with isolated hydrated components. Minimizes JS; `client:idle`/`client:visible` directives control hydration timing. Best for content-heavy, low-interaction pages.
- **RSC** (React Server Components): components run only on server, zero client JS for them, stream serialized tree; `"use client"` marks the hydration boundary. Server components can't use state/effects/browser APIs; props crossing the boundary must be serializable (no functions/class instances). Reduces bundle by keeping data-fetching + heavy deps server-side.
- **Edge** (render at PoP): low-latency personalization (geo, A/B) but constrained runtime (no Node built-ins, limited CPU/memory, cold caveats). Move data-adjacent work to edge only if data is also near the edge.
- Rule: pick per-**route**, not per-app. Marketing=SSG/ISR, dashboard=CSR/RSC, product page=SSR/streaming.

## Micro-frontends
- **Module Federation** (webpack 5 / `@module-federation/*` for Vite/rspack): runtime import of remote-exposed modules; `shared` singletons (react, react-dom) with `singleton:true, requiredVersion` to avoid duplicate React (two Reacts = broken hooks/context). Eager vs lazy shared; version mismatch → fallback download or hard error.
- **Import maps** (native): browser-level bare-specifier → URL mapping; SystemJS polyfill for older targets. Simple, no bundler coupling, but no shared-dep dedup logic beyond the map.
- **single-spa**: lifecycle orchestration (bootstrap/mount/unmount) of independently-deployed apps on one page; framework-agnostic.
- **When NOT to**: one team, shared release cadence, tight cross-app UX, or perf-critical (MFE adds runtime overhead, duplicated vendor bytes, version-skew bugs). MFE solves *org/deploy* independence, not code reuse — a shared npm package/monorepo is usually the right answer.
- **Shared state across MFEs**: prefer URL + backend as source of truth; for cross-app events use a thin event bus (CustomEvent / broadcast) with a versioned contract, not a shared mutable store. Never share a framework store instance across independently-versioned bundles.

## Monorepo tooling
- **Turborepo**: task graph from `dependsOn` (`^build` = deps first); content-hash based caching keyed on inputs (files + env + deps); `--filter` for scoping; remote cache (Vercel/self-host) shares artifacts across CI + devs. `outputs` must be declared or cache stores nothing.
- **Nx**: richer project graph, affected commands (`nx affected -t build` from git diff base), computation caching, generators/executors, module boundary lint rules (`@nx/enforce-module-boundaries` with tags).
- **Affected builds**: compute changed projects vs merge-base; only build/test the impacted subgraph — the core CI speedup at scale.
- **Cache correctness**: any un-declared input (env var, `.env`, tool version, timestamp) → stale hits or false misses. Declare all inputs; treat cache poisoning as a real incident.

## Design systems + tokens
- **Tokens** as single source: primitive → semantic → component layers (`color.blue.500` → `color.action.primary` → `button.bg`). Style Dictionary / Tokens Studio compile to CSS vars, TS, iOS/Android. Theming via semantic-layer swap (CSS custom properties at `:root`/`[data-theme]`), never hardcoded values in components.
- Distribute component library as versioned package; enforce visual regression (Chromatic/Playwright snapshots). Breaking token rename = major version.

## Dependency boundaries + layering
- Enforce direction: `app → features → entities → shared` (Feature-Sliced) or domain layers; forbid upward/sideways imports via `eslint-plugin-boundaries`, `dependency-cruiser`, Nx tags, or TS project references. Detect cycles in CI (`madge --circular`).
- **Contracts/versioning**: shared packages expose a stable public API (`exports` map, no deep imports); semver + changesets for coordinated releases; consumer-driven contract tests for MFE/API seams.

## Performance budgets in CI
- Budget bytes per route (`bundlesize`/`size-limit`), Lighthouse CI assertions (LCP, TBT, CLS thresholds), fail PR on regression. Track initial JS, per-route chunks, third-party weight. `webpack-bundle-analyzer`/`rollup-plugin-visualizer` in CI artifacts.
- INP is the interactivity budget now (not FID); watch long tasks + hydration cost.

## RSC data + caching model
- Data fetching in server components: `await`-ed fetches run on server, dedup'd + cached per request; colocate data next to the component that needs it (kills prop-drilling + client waterfalls). Parallelize with `Promise.all` or independent `<Suspense>` boundaries so one slow query doesn't block the shell.
- Next App Router cache layers: request memoization (per render) → Data Cache (`fetch` cache, `revalidate`/`tags`) → Full Route Cache → Router Cache (client, prefetch). Mis-set cache = stale UI or cache stampede; use `tags` + `revalidateTag` for targeted busting, `dynamic = 'force-dynamic'` to opt out.
- Server Actions (`"use server"`): mutations without an API route; validate + authz *inside* the action (it's a public POST endpoint), never trust the client-passed args.

## Experimentation + flags
- Flags as a decoupling layer: ship dark, ramp by cohort, kill switch. Evaluate server-side (in RSC/SSR) to avoid flicker + client bundle leakage of variant code. SSR + flags interacts with CDN cache keys — vary cache on flag bucket or render at edge.
- A/B without CLS: reserve layout, resolve variant before paint (edge/SSR), or accept flicker only below the fold.

## Build vs buy design system
- Buy (MUI/Chakra/Radix) for speed + a11y primitives; build the token/theme + composition layer on top. Radix/React-Aria = unstyled behavior/a11y, you own the visuals via tokens — best balance at scale. Full custom only when brand/perf demands justify the maintenance + a11y burden (focus management, ARIA, keyboard nav are the hard 80%).

## Testing at scale
- Pyramid inverts toward integration: component tests (Testing Library) + a thin layer of E2E (Playwright) on critical journeys; visual regression on the design system; contract tests on MFE/API seams; type-level as the cheapest gate. Parallelize + shard E2E; flake budget enforced (quarantine, not ignore).

## Large-team strategies
- Codeowners per boundary; trunk-based + feature flags over long-lived branches; automated codemods (jscodeshift/ts-morph) for cross-cutting migrations; API/GraphQL schema as versioned contract (breaking-change lint, deprecation windows); incremental adoption via strangler pattern (new architecture behind a route/flag, migrate leaf-first).
- **Module Federation versioning**: remotes deploy independently → shell must tolerate remote schema drift; pin shared singletons, publish a compatibility matrix, and gate remote loads behind error boundaries + fallback UI so one broken remote doesn't white-screen the shell.

## Gotchas -> Fix
- **Two React copies** (MFE/federation) → hooks throw "invalid hook call", context returns undefined -> mark react/react-dom `singleton` + `requiredVersion`; verify one instance in prod, not just dev.
- **RSC serialization boundary** passing a function/Date/class as prop → runtime error -> pass serializable data only; keep event handlers in `"use client"` children.
- **Streaming SSR buffered** by nginx/CDN → whole benefit lost, user waits for full doc -> disable proxy buffering (`proxy_buffering off`), ensure Transfer-Encoding: chunked survives.
- **ISR stale-first** surprises after data change -> use on-demand `revalidateTag`, not just time-based, for correctness-critical content.
- **Turbo/Nx cache false hit** from undeclared env input -> add to `inputs`/`env`; a "works locally fails in CI" that flips with cache clear is the tell.
- **Hydration mismatch** (server vs client HTML differ: `Date.now()`, `localStorage`, random, locale) → React discards SSR HTML and re-renders -> gate client-only values behind `useEffect`/`useSyncExternalStore`, or `suppressHydrationWarning` narrowly.
- **Design-token drift**: components hardcode hex → theming breaks silently -> lint for raw color/spacing literals; only semantic tokens allowed.
- **MFE version skew**: shared lib bumped in one remote → subtle runtime breakage -> pin shared singletons, contract-test the seam, deploy shell + remotes with compatibility matrix.
- **Deep imports** into a package's internals bypass `exports` and break on refactor -> set `"exports"` map to expose only public entry; block deep paths.
- **Edge runtime** using Node APIs (`fs`, `Buffer`, native crypto) → deploy-time or cold runtime failure -> check the edge-compatible API subset; keep Node-only work in serverless/SSR functions.
- **Per-app rendering choice** forced everywhere → dashboards pay SEO SSR cost, marketing ships heavy CSR -> choose per route.
- **Budget without enforcement** → drift returns in weeks -> make it a failing CI gate, not a dashboard.
