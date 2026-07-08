# Browser APIs

## fetch + AbortController
- Cancel on unmount/re-query: `const c = new AbortController(); fetch(url, { signal: c.signal }); c.abort()` — abort rejects with `DOMException` name `AbortError`; filter it out of error reporting.
- Timeout: `AbortSignal.timeout(5000)` as `signal` (rejects with `TimeoutError`); combine signals with `AbortSignal.any([userSignal, AbortSignal.timeout(5000)])`.
- fetch does NOT reject on HTTP errors — check `res.ok` / `res.status` before `res.json()`. It rejects only on network failure/CORS/abort.
- Response body is single-read: `res.json()` twice throws — `res.clone()` if two consumers need it.
- Send cookies cross-origin: `credentials: 'include'` (server must send `Access-Control-Allow-Credentials: true` and a non-wildcard origin).
- Streaming: `for await (const chunk of res.body)` or `res.body.getReader()`; decode with `TextDecoder({ stream: true })`.
- `keepalive: true` (or `navigator.sendBeacon`) for requests during page unload; body capped ~64KB.

## Storage
- `localStorage`: synchronous (blocks main thread), strings only, ~5MB, shared per-origin across tabs; `storage` event fires in OTHER tabs only. Not available in workers.
- `sessionStorage`: per-tab, survives reload but not tab close.
- IndexedDB: async, structured-clone objects/blobs, GBs of quota; use the `idb` npm wrapper (`openDB`, `db.put('store', val, key)`) — the raw event API is painful. Works in workers.
- IndexedDB transactions auto-commit when the microtask queue drains — an `await fetch()` mid-transaction kills it ("TransactionInactiveError"); do all IO before or after.
- Persistence: `navigator.storage.persist()` requests eviction protection; `navigator.storage.estimate()` for quota/usage.
- Never store secrets/tokens in localStorage if XSS is a concern — any injected script can read it.

## Workers
- Web Worker: `new Worker(new URL('./w.js', import.meta.url), { type: 'module' })` — bundler-friendly form. Communicate via `postMessage` (structured clone); transfer big buffers zero-copy: `postMessage(buf, [buf])`.
- No DOM in workers; `fetch`, IndexedDB, `OffscreenCanvas`, WebSocket all work.
- SharedWorker: one instance shared by all same-origin tabs (not in Chrome for Android).
- Service Worker: network proxy for offline/caching/push; lifecycle: install → waiting → activate; `self.skipWaiting()` + `clients.claim()` to take over immediately. Updates are byte-compared and applied on next navigation.

## Observers
- IntersectionObserver: lazy load / infinite scroll / "in view" analytics: `new IntersectionObserver(entries => ..., { rootMargin: '200px', threshold: 0 })` — `rootMargin` preloads before visible. Remember `observer.unobserve(el)` after one-shot loads.
- ResizeObserver: element-level responsive logic; callback gets `entry.contentRect` / `borderBoxSize[0].inlineSize`. "ResizeObserver loop completed with undelivered notifications" = you resized what you observe; benign if intentional, but break the cycle.
- MutationObserver: watch DOM changes (`{ childList: true, subtree: true }`) — prefer it over polling for third-party DOM.

## Clipboard
- Write: `await navigator.clipboard.writeText(text)` — requires secure context (HTTPS) and (in Chrome) transient user activation or `clipboard-write` permission.
- Read: `navigator.clipboard.readText()` prompts a permission in Chrome; Safari requires it inside a user gesture and may show a paste confirmation.
- Rich content: `new ClipboardItem({ 'text/html': blob, 'text/plain': blob2 })`; Safari needs the promise-based `ClipboardItem` form for async data.

## History & URL
- `history.pushState(state, '', '/path?x=1')` changes URL without navigation; listen to `popstate` for back/forward — `pushState` itself does NOT fire `popstate`.
- Modern: Navigation API (`navigation.addEventListener('navigate', e => e.intercept({ handler }))`) — Chromium + Safari 18+, not yet Firefox-stable everywhere; feature-detect.
- Parse/build URLs with `new URL(href, base)` and `url.searchParams.set('q', v)` — never string-concat query strings.
- `URL.canParse(str)` for validation without try/catch.

## Notifications & Permissions
- `Notification.requestPermission()` must follow a user gesture; if the user denies, you can never re-prompt — gate behind your own pre-prompt UI.
- Page notifications need the page open; push notifications need a Service Worker + Push API + a push service (VAPID keys).
- Query without prompting: `navigator.permissions.query({ name: 'clipboard-read' | 'geolocation' | 'notifications' })` → `granted | denied | prompt`; listen to `status.onchange`.

## Cross-tab & coordination
- `BroadcastChannel('app')`: `channel.postMessage(data)` reaches every same-origin tab/worker except the sender — logout propagation, cache invalidation, leader announcements.
- Web Locks: `navigator.locks.request('sync-job', async lock => {...})` — only one tab runs the critical section; `{ ifAvailable: true }` for try-lock, `navigator.locks.query()` to inspect.
- `document.visibilityState` + `visibilitychange` for pausing polling/animation in hidden tabs; background tabs get timers throttled (≥1s, chained timers up to 1/min) — never rely on `setInterval` accuracy when hidden.
- Page lifecycle: use `pagehide`/`visibilitychange` for save-on-exit (fires on mobile app-switch); `unload` is unreliable and kills bfcache.

## Files & misc
- File picking without `<input>`: `showOpenFilePicker()` / `showSaveFilePicker()` (Chromium-only) return handles with `createWritable()`; fallback to `<input type="file">` + download-link blob.
- Read user files: `file.text()`, `file.arrayBuffer()`, `file.stream()` — FileReader is legacy.
- Drag-drop uploads: `drop` event `e.dataTransfer.files`; must `preventDefault()` on `dragover` or the browser navigates to the file.
- `structuredClone(obj)` — deep clone with cycles, Maps, Dates; no more JSON round-trip.

## Gotchas -> Fix
- **AbortError spamming Sentry**: filter `err.name === 'AbortError'` before reporting.
- **fetch "succeeded" with a 500**: check `res.ok`; throw with status + body text for real error handling.
- **localStorage QuotaExceededError in Safari private mode (legacy) or when full**: wrap set in try/catch; degrade gracefully.
- **JSON.parse crash on corrupted stored value**: try/catch around every `JSON.parse(localStorage.getItem(...))`; treat parse failure as empty.
- **IndexedDB transaction dies after await**: collect data first, then open the transaction and issue all requests synchronously.
- **IntersectionObserver never fires**: target is `display:none`, observer created after element removed, or `root` isn't an ancestor scroll container.
- **Clipboard write fails "Document is not focused"**: DevTools focus or async gap after the click; call clipboard write directly in the click handler.
- **Service worker serves stale app forever**: cache-first HTML with no update path — network-first for navigations or add an "update available" toast on `updatefound`.
- **`storage` event not firing**: it only fires in other tabs/windows, never the one that wrote; use `BroadcastChannel` for same-tab-family messaging.
- **Worker file 404 in production**: bare `new Worker('/w.js')` bypasses the bundler; use the `new URL(..., import.meta.url)` pattern.
- **Geolocation/camera prompt blocked**: requires secure context and often user gesture; iframe needs `allow="geolocation; camera"` Permissions-Policy.
