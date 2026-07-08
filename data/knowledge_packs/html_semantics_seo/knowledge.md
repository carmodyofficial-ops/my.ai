# HTML Semantics & SEO

## Document structure & landmarks
- Skeleton: `<header>` (banner), `<nav>`, `<main>` (exactly one, not nested in others), `<aside>`, `<footer>` (contentinfo) — these map to ARIA landmarks for free.
- `<article>` = self-contained/syndicatable (post, card, comment); `<section>` = thematic grouping that should have a heading; bare wrapper → `<div>`.
- Headings: one `<h1>` per page (the page's topic), strictly nested levels, no skipping h2→h4. Search engines and screen readers both build outlines from them.
- `<html lang="en">` always; per-fragment `lang` for foreign-language quotes.
- `<time datetime="2026-07-08">`, `<figure>/<figcaption>`, `<address>` (contact info), `<dl>` for key-value pairs — semantics search engines can parse.

## Meta & Open Graph
- `<title>`: unique per page, ~50-60 chars, primary keyword early, brand last ("Blue Widgets — Acme").
- `<meta name="description" content="...">`: ~150-160 chars; not a ranking factor but drives snippet CTR; Google rewrites bad ones.
- Required for previews: `og:title`, `og:description`, `og:image` (1200×630, absolute URL), `og:url`, `og:type`; Twitter/X: `<meta name="twitter:card" content="summary_large_image">`.
- `<meta name="viewport" content="width=device-width, initial-scale=1">` — mobile-first indexing means the mobile render is THE render.
- Meta `keywords` is dead — ignored by Google since 2009; don't ship it.

## Structured data (JSON-LD)
- Preferred format: `<script type="application/ld+json">` with schema.org types — `Article`, `Product` (+ `offers`, `aggregateRating`), `FAQPage`, `BreadcrumbList`, `Organization`, `JobPosting`, `Event`, `Recipe`.
- Minimal Article: `{"@context":"https://schema.org","@type":"Article","headline":"...","datePublished":"2026-07-08","author":{"@type":"Person","name":"..."}}`.
- Structured data must match visible page content — mismatches risk manual actions.
- Validate with Google's Rich Results Test and schema.org validator; rich results are eligibility, not a guarantee.

## Canonical, robots, sitemaps
- `<link rel="canonical" href="https://example.com/page">` — absolute URL, self-referencing on the primary version; dedupes UTM/query/session variants. One per page; conflicting canonicals get ignored.
- robots.txt controls CRAWLING, not indexing: a blocked URL can still be indexed (URL-only, from external links). To deindex: allow crawling + `<meta name="robots" content="noindex">` (or `X-Robots-Tag: noindex` header for non-HTML).
- Never combine `Disallow` in robots.txt with `noindex` on the same URL — the bot can't see the noindex.
- sitemap.xml: canonical URLs only (no redirects, no noindexed pages), `<lastmod>` honest or omitted, ≤50k URLs/50MB per file, index file for more; reference it in robots.txt (`Sitemap: https://.../sitemap.xml`) and submit in Search Console.
- Pagination: unique canonicals per page (`?page=2` canonicals to itself, not page 1); `rel=prev/next` is no longer used by Google.

## SSR vs CSR for SEO
- Google renders JS (Chromium-based WRS) but rendering is queued/deferred — client-only content can be indexed late or missed; other engines and most link-preview scrapers execute no JS at all.
- OG tags MUST be in the server-delivered HTML — social scrapers never run JS.
- Safe ranking-critical setup: SSR/SSG/ISR (Next.js, Astro, Remix) for content pages; CSR is fine for logged-in app surfaces you don't want indexed anyway.
- Avoid: content behind click/scroll-only JS, hash-based routing (`#/page` — one URL to Google), meta tags set only via client-side `useEffect`/Helmet.
- Soft 404s: SPA "not found" screens returning HTTP 200 — return a real 404/410 status server-side (or at least `noindex` the not-found state).

## Links & media
- Descriptive anchor text ("pricing plans", not "click here") — anchor text is a ranking signal for the target.
- Internal linking: every important page reachable within ~3 clicks; orphan pages don't get crawled reliably.
- `rel="nofollow"` (don't vouch), `rel="sponsored"` (paid), `rel="ugc"` (user content); `noopener` is default with `target="_blank"` in modern browsers.
- Image SEO: descriptive filenames + `alt`; specify `width`/`height` (CLS is a ranking-relevant page-experience signal).
- Redirects: permanent moves = 301/308 (passes signals); avoid chains >2 hops; never redirect everything to the homepage (treated as soft 404).

## Head extras & crawl hygiene
- Favicons: `<link rel="icon" href="/favicon.ico" sizes="32x32">` + `<link rel="icon" type="image/svg+xml" href="/icon.svg">` + `<link rel="apple-touch-icon" href="/apple-touch-icon.png">` (180×180); Google shows favicons in results.
- `<link rel="manifest">` + theme-color for installability; not an SEO signal but part of a complete head.
- Status codes matter: 404 = keep trying a while, 410 = gone (drops faster), 301 = permanent (signals transfer), 302 = temporary (canonical stays on source), 5xx sustained = crawl rate drops and pages can fall out.
- Crawl budget only matters at scale (100k+ URLs): kill infinite faceted-URL spaces (parameter combinations) with robots.txt patterns + canonicals, keep redirect chains short, return 304 for unchanged pages.
- `nosnippet`, `max-snippet:N`, `max-image-preview:large` robots directives tune result display; `data-nosnippet` attribute excludes fragments.
- Search Console: URL Inspection shows the rendered HTML Google saw — the ground truth when debugging "why isn't this indexed".

## Gotchas -> Fix
- **Page indexed but "Blocked by robots.txt" styling/JS**: blocked assets break rendering — allow CSS/JS paths in robots.txt.
- **Duplicate content across http/https, www/apex, trailing slash**: pick one canonical host+form, 301 the rest, self-canonical everywhere.
- **OG image not showing on Slack/X**: tag injected client-side or relative URL — SSR the tags, absolute `og:image`, re-scrape with the platform's debugger (e.g., opengraph validators, Facebook Sharing Debugger).
- **`noindex` page still in results**: robots.txt blocks crawling so Google never sees the noindex — unblock, let it recrawl, then it drops.
- **Multiple h1s from component reuse**: demote component headings; heading level should come from page context (pass it as a prop).
- **Canonical to a redirecting/404 URL**: canonicals are hints and get discarded — point to a live 200 page.
- **Infinite scroll content invisible to crawlers**: paired paginated URLs (`?page=N`) with real links, or ensure content is server-rendered.
- **Localized pages compete with each other**: `hreflang` annotations (each page lists all alternates + `x-default`, must be bidirectional).
- **Staging site indexed**: password-protect or `X-Robots-Tag: noindex` at the edge — robots.txt Disallow alone still leaks URLs into the index.
- **JSON-LD errors ignored silently**: invalid JSON (trailing commas, smart quotes) kills the whole block — lint it; test in Rich Results Test.
- **Titles/descriptions identical site-wide (templated)**: generate per-page from content; duplicate titles dilute relevance and get rewritten.
- **Query-param variants (`?sort=`, `?utm_`) flooding the index**: self-canonical to the clean URL on every variant; keep tracking params out of internal links.
- **Lazy-loaded images missing from Google Images**: JS-only lazy loading without `<img src>` fallback — use native `loading="lazy"` with a real `src`/`srcset` in the HTML.
