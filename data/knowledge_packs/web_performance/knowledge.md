# Web Performance

## Core Web Vitals: causes -> fixes
- **LCP (Largest Contentful Paint, good ≤ 2.5s)** — usually the hero image or headline. Fixes: serve the LCP image from HTML (not CSS background or JS-inserted), `<link rel="preload" as="image" fetchpriority="high">` or `fetchpriority="high"` on the `<img>`, never lazy-load it, compress/resize, cut server TTFB (CDN, cache), eliminate render-blocking CSS/JS before it.
- **INP (Interaction to Next Paint, good ≤ 200ms; replaced FID in 2024)** — long main-thread tasks. Fixes: break up work (`scheduler.yield()` / `setTimeout` chunking / `requestIdleCallback`), debounce input handlers, move computation to Web Workers, reduce hydration cost, avoid layout thrash in handlers (batch reads then writes), CSS `content-visibility: auto` on offscreen sections.
- **CLS (Cumulative Layout Shift, good ≤ 0.1)** — content jumping. Fixes: explicit `width`/`height` (or `aspect-ratio`) on images/video/iframes/ads, reserve space for late-loading UI, `font-display: optional` or size-adjusted fallback fonts, never insert banners above existing content, animate with `transform` not `top/left/height`.
- Field vs lab: CrUX/`web-vitals` npm package (`onLCP`, `onINP`, `onCLS`) = real users; Lighthouse = lab, no INP (uses TBT as proxy).

## Images
- Formats: AVIF < WebP < JPEG for photos; SVG for icons/logos. `<picture><source type="image/avif">...<img></picture>` for fallbacks.
- Responsive: `srcset="a-400.jpg 400w, a-800.jpg 800w" sizes="(max-width: 600px) 100vw, 50vw"` — `sizes` wrong = browser downloads the biggest.
- `loading="lazy"` on below-the-fold `<img>`/`<iframe>` only; `decoding="async"` is a cheap default.

## Fonts
- Self-host; preload the primary WOFF2: `<link rel="preload" href="/f.woff2" as="font" type="font/woff2" crossorigin>` (crossorigin required even same-origin).
- `font-display: swap` avoids invisible text (FOIT) but risks CLS; pair with fallback metrics tuning (`size-adjust`, `ascent-override`) or use `optional` for zero-shift.
- Subset (`unicode-range`, `pyftsubset`) — most webfont bytes are unused glyphs. `woff2` only; drop older formats.

## JS & bundles
- Route-based code splitting first (`import()` per route), then component-level for heavy widgets (charts, editors). In React: `lazy()` + `Suspense`.
- `<script defer>` (ordered, after parse) or `type="module"` (deferred by default); `async` only for independent scripts (analytics). Inline scripts block parsing.
- Audit: `rollup-plugin-visualizer` / `webpack-bundle-analyzer` / `source-map-explorer`. Common wins: replace moment (→ date-fns/dayjs), lodash full import (→ `lodash-es` named imports), duplicate deps in the lockfile.
- Ship modern JS (`browserslist` defaults); transpiling to ES5 roughly doubles size for no modern-browser benefit.

## Render-blocking & critical path
- CSS in `<head>` blocks render; JS without defer/async blocks parsing. Inline critical CSS, load the rest with media tricks or split per route.
- `<link rel="preconnect" href="https://cdn...">` for critical third-party origins; `dns-prefetch` as cheap fallback.
- Third-party scripts: load after interactive, use facades (e.g., lite-youtube-embed) instead of full embeds.

## Caching
- Hashed static assets (`app.3f9c.js`): `Cache-Control: public, max-age=31536000, immutable`.
- HTML: `Cache-Control: no-cache` (revalidate every time, ETag/Last-Modified make it a cheap 304) — never long-cache HTML that references hashed assets.
- APIs: `private, max-age=0, must-revalidate` unless deliberately cacheable; `stale-while-revalidate=60` for tolerant freshness.
- `Vary: Accept-Encoding` handled by CDNs; beware `Vary: Cookie`/`*` killing cache hit rates.

## Measuring
- Lighthouse (DevTools > Lighthouse or `npx lighthouse URL`): run against production builds, throttled; scores are lab-only and vary ±few points run-to-run.
- DevTools Performance panel: record an interaction, look for long tasks (>50ms, red-flagged), forced reflow warnings, and the LCP marker.
- Performance panel Insights + `PerformanceObserver`: `new PerformanceObserver(cb).observe({type:'largest-contentful-paint', buffered:true})` for custom RUM.
- WebPageTest for filmstrips/waterfalls; CrUX dashboard / PageSpeed Insights for 28-day field data.

## Resource hints & priorities
- Order of power: `preload` (fetch this now, current page) > `preconnect` (open the connection) > `prefetch` (idle-time, next navigation) > `dns-prefetch`.
- `fetchpriority="high|low"` on `<img>`, `<link>`, `<script>`, and fetch(`{ priority }`) — demote carousels/below-fold (`low`), promote the LCP image.
- Don't preload more than 2-3 resources; over-preloading steals bandwidth from the critical path and Chrome warns about unused preloads.
- Speculation Rules API (Chromium): `<script type="speculationrules">{"prerender":[{"where":{"href_matches":"/products/*"}}]}</script>` — near-instant next-page navigations; `moderate` eagerness triggers on hover.

## bfcache & navigation
- Back/forward cache makes back-navigation instant; killers: `unload` handlers (use `pagehide`), `Cache-Control: no-store` on the HTML, open WebSocket/IndexedDB transactions at navigation.
- Test in DevTools > Application > Back/forward cache; listen for restore via `pageshow` with `event.persisted === true` (re-sync any stale UI there).
- SPA soft navigations: measure route-change performance yourself (custom marks: `performance.mark`/`measure`) — CWV mostly reflects the initial load.

## Gotchas -> Fix
- **Lazy-loaded hero image tanks LCP**: remove `loading="lazy"` from above-the-fold images; add `fetchpriority="high"`.
- **`sizes` omitted with `srcset`**: defaults to `100vw`; browser over-downloads — always set `sizes` for non-full-width images.
- **Preloaded font still swaps late**: missing `crossorigin` on the preload makes the browser fetch it twice (preload ignored).
- **CLS from web fonts only in the field**: lab has fonts cached; use fallback font metric overrides or `font-display: optional`.
- **INP fine in Lighthouse, bad in field**: Lighthouse doesn't measure INP; profile real interactions in the Performance panel with CPU throttling (4-6x).
- **`document.querySelector` loop causing layout thrash**: reading `offsetHeight`/`getBoundingClientRect` after writes forces sync reflow per iteration — batch all reads, then all writes, or use `requestAnimationFrame`.
- **Bundle grows after adding one icon**: whole icon library imported; import per-icon paths or use an SVG sprite.
- **Cache never hits after deploy**: HTML cached long-term keeps referencing old hashed files (or 404s); HTML must be `no-cache`.
- **Third-party tag manager dominates main thread**: load on interaction/idle, audit tags quarterly, use `async` + facade patterns.
- **300ms+ handler blamed on your code**: check for synchronous `localStorage`/`JSON.parse` of large blobs and excessive React re-renders (memoize, virtualize long lists).
- **`content-visibility: auto` breaks scrollbar/anchor jumps**: set `contain-intrinsic-size: auto 500px` to reserve estimated space.
- **Score drops only on mobile**: Lighthouse mobile applies 4x CPU slowdown + slow-4G; your dev machine hides main-thread cost — always test throttled.
- **Compression missing on API/JSON responses**: enable gzip at minimum, brotli (`br`) for static assets — text payloads shrink 60-80%; verify `content-encoding` in the Network panel.
- **Infinite list scroll jank**: DOM node count in the thousands — virtualize (`@tanstack/react-virtual`, `content-visibility`) so only visible rows render.
