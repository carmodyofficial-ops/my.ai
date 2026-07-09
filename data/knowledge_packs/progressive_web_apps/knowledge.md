# Progressive Web Apps
## Web app manifest
- `manifest.webmanifest` linked via `<link rel="manifest">`. Keys: `name`, `short_name`, `start_url`, `scope`, `display` (`standalone`/`fullscreen`/`minimal-ui`), `theme_color`, `background_color`, `icons`.
- Installability: HTTPS + manifest with name + 192px & 512px icons + a registered service worker with a fetch handler. Add a `maskable` icon (`purpose:"maskable"`) for adaptive shapes.
## Service worker lifecycle
- Registers on a scope (path). Events: `install` (precache assets) → `activate` (clean old caches, `clients.claim()`) → `fetch` (intercept requests).
- New SW `install`s but stays `waiting` until all old-controlled tabs close. `self.skipWaiting()` in install + `clients.claim()` in activate to take over immediately.
- Runs off the main thread, no DOM. HTTPS only (localhost exempt). Scope can't exceed the SW file's directory unless `Service-Worker-Allowed` header set.
## Caching strategies (in `fetch`)
- **Cache-first**: check cache, fall back to network. For hashed/immutable static assets. Fastest, risks staleness.
- **Network-first**: try network, fall back to cache. For HTML/API where freshness matters offline.
- **Stale-while-revalidate**: serve cache immediately, fetch + update cache in background. Best UX for semi-dynamic.
- **Cache-only / Network-only**: for precached shell / non-cacheable POSTs.
- Version cache names (`static-v3`); delete non-matching in `activate`. Workbox automates these + precache manifests.
## Workbox
- `precacheAndRoute(self.__WB_MANIFEST)` — build tool injects a manifest of `{url, revision}`; revision hash busts precache automatically, so bump on content change (no manual cache version).
- `registerRoute(match, strategy)` — match by string/RegExp/function. Strategies: `CacheFirst`, `NetworkFirst`, `StaleWhileRevalidate`, `NetworkOnly`, `CacheOnly`.
- Plugins per route: `ExpirationPlugin({maxEntries, maxAgeSeconds})` to cap runtime caches, `CacheableResponsePlugin({statuses:[0,200]})` to allow opaque, `BackgroundSyncPlugin` for retry queues.
- Precache = versioned app shell (fixed set, cleaned on activate). Runtime cache = dynamically fetched (images, API) — always cap size/age or it grows unbounded.
## Offline
- App shell pattern: precache HTML/CSS/JS shell on install → instant offline load; hydrate data from cache/IndexedDB. Provide an offline fallback page for navigations.
- Offline fallback: on `fetch` for a navigation, `catch` → serve a precached `/offline.html`. For images, fall back to a placeholder from cache.
- Only GET is cacheable; queue mutating requests for Background Sync.
## IndexedDB
- Async, transactional, large-capacity structured store for offline data/outbox — use the `idb` wrapper (promises) over the raw event API. Accessible from both page and SW.
- Store app data + a mutation outbox (queued POSTs) here; drain it on reconnect. Don't put big blobs in Cache Storage keyed by fake requests — use IndexedDB. `localStorage` is sync + tiny + string-only + not SW-accessible; avoid for PWA state.
## Install prompt
- `beforeinstallprompt` fires (Chromium); `e.preventDefault()`, stash `e`, show your own button, later `e.prompt()` then await `e.userChoice`. Can't call `prompt()` outside a user gesture.
- iOS Safari: no `beforeinstallprompt` — users add via Share → Add to Home Screen. `appinstalled` event confirms install.
## Update flow (prompt-to-refresh)
- Detect: on `navigator.serviceWorker.register`, listen for `updatefound` → new worker `statechange` to `installed` while `controller` exists = update waiting. Show a "New version" toast.
- Activate on click: `postMessage({type:'SKIP_WAITING'})` → SW calls `self.skipWaiting()`. Reload once on the subsequent `controllerchange` (guard with a flag to avoid loops).
- `skipWaiting` + `clients.claim()` auto-updates silently but can swap assets under a live tab (version mismatch) — prefer the prompt for apps with unsaved state.
## Background & Periodic Sync
- Background Sync: `registration.sync.register('tag')`; SW `sync` event fires when connectivity returns — drain the IndexedDB outbox here for deferred POSTs. Browser retries with backoff; one-shot per registration.
- Periodic Sync (`periodicsync`, `registration.periodicSync.register`): background content refresh at browser-chosen intervals; requires installed PWA + high engagement; Chromium-only. Feature-detect.
## Push (VAPID) flow
- Generate a VAPID keypair; expose the public key. `pushManager.subscribe({userVisibleOnly:true, applicationServerKey:<vapidPublicKey>})` → `PushSubscription` (endpoint + keys) → POST to server.
- Server signs a Web Push request (VAPID JWT) to the endpoint (payload encrypted with the subscription keys) → SW `push` event → MUST `event.waitUntil(showNotification(...))`.
- Handle `notificationclick` (focus/open a client) and `pushsubscriptionchange` (re-subscribe, update server). Prune dead subscriptions on 404/410 from the push service.
## Installability criteria
- HTTPS + linked manifest with `name`/`short_name`, `start_url`, `display: standalone`(or fullscreen/minimal-ui), 192px & 512px icons + a `maskable` icon, and a registered SW with a `fetch` handler. Missing any → no install prompt.
## Update flow gotchas -> Fix
- **Stale app after deploy**: users stuck on old SW until every tab closes. Fix: `skipWaiting` + `clients.claim`, or prompt "New version available — reload" via `updatefound`/`controllerchange`.
- **Reload loop from `controllerchange`**: auto-reloading on activate loops. Fix: guard with a `refreshing` flag; reload once.
- **HTML cached forever**: cache-first on the shell serves an outdated index that references deleted hashed assets. Fix: network-first (or SWR) for HTML/navigations; cache-first only for hashed assets.
- **SW file itself cached**: browser caches `sw.js` so updates never ship. Fix: serve `sw.js` with `Cache-Control: no-cache`/max-age=0; browsers also byte-compare on each navigation.
- **Old caches never cleaned**: storage bloat. Fix: delete caches not in the current version allowlist during `activate`.
- **Scope too narrow**: SW at `/js/sw.js` can't control `/`. Fix: serve SW from root or set `Service-Worker-Allowed`.
- **Caching POST/opaque responses**: opaque (no-cors) responses have status 0 and can't be validated. Fix: don't cache POSTs; avoid caching opaque unless intentional.
- **`beforeinstallprompt` never handled**: default mini-infobar shown or nothing. Fix: capture + `preventDefault`; trigger `prompt()` from a click.
- **Push without visible notification**: browser revokes push permission. Fix: always `showNotification` in `push` handler.
- **Assuming service worker on iOS parity**: no push (older iOS), no install prompt API. Fix: feature-detect, graceful fallback.
- **Testing against cached SW**: DevTools → Application → "Update on reload" + "Bypass for network" during dev.
- **iOS/Safari limitations**: push only for installed (Add to Home Screen) apps on iOS 16.4+; no Background/Periodic Sync; ~50MB storage + eviction after weeks unused; no `beforeinstallprompt`; each installed PWA gets a fresh storage/login state. Fix: feature-detect everything; keep offline data small; re-auth gracefully.
- **Runtime cache grows unbounded**: image/API caches balloon, hit quota eviction. Fix: `ExpirationPlugin` maxEntries/maxAgeSeconds per route.
- **Precache revision not bumped**: same URL, new content, stale precache. Fix: use build-injected `__WB_MANIFEST` revisions (or content-hashed filenames).
- **`skipWaiting` swaps assets mid-session**: live tab loads chunks from a new deploy that no longer exist. Fix: prompt-to-refresh instead of silent skipWaiting; hash + long-cache chunks so old ones stay fetchable.
- **Storage quota exceeded**: writes throw `QuotaExceededError`. Fix: check `navigator.storage.estimate()`, request `persist()`, evict old entries proactively.
- **Outbox lost on retry failure**: Background Sync unsupported (Safari) → queued POSTs never sent. Fix: also drain the IndexedDB outbox on `online`/app-foreground as a fallback.
- **Notification permission prompt on load**: users deny reflexively. Fix: request from a user gesture, in context, after showing value.
