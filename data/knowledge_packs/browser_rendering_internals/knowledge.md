# Browser Rendering Internals

## Critical rendering path
- Pipeline: bytes → tokens → **DOM** (HTML parse, incremental) ‖ **CSSOM** (CSS parse, render-blocking) → **Render tree** (DOM ∩ visible styles; `display:none` excluded, `visibility:hidden` included) → **Layout/reflow** (geometry, box positions) → **Paint** (fill pixels into layers) → **Composite** (GPU assembles layers to screen).
- CSS is render-blocking: the browser won't paint until CSSOM is built; JS is parser-blocking (a `<script>` blocks DOM construction and waits for pending CSSOM before executing, since it may read styles). `defer` = execute after DOM parse, in order; `async` = execute ASAP out of order; module scripts are `defer` by default.
- Preload scanner speculatively fetches sub-resources while parser is blocked. `<link rel=preload>`/`preconnect` to prioritize; avoid `@import` (serializes CSS fetches).
- First render needs DOM + CSSOM. Minimize critical CSS (inline above-the-fold), defer non-critical CSS (`media` trick / `rel=preload` swap).

## Reflow vs repaint vs composite
- **Reflow (layout)**: geometry changes — width/height/top/left/margin/padding/font-size/adding-removing DOM/reading offset. Most expensive; can cascade to ancestors/descendants/whole document.
- **Repaint**: visual-only, no geometry — color, background, `visibility`, `box-shadow`, `outline`. Skips layout, still rasterizes.
- **Composite-only**: `transform` and `opacity` (and `filter` on a composited layer) — handled on the compositor thread/GPU, skip layout AND paint. Animate ONLY these for 60fps; animating `top`/`left`/`width` forces reflow every frame.
- Property cost cheat: `transform`/`opacity` → composite; `color`/`background` → paint; `left`/`width`/`display`/`font` → layout.

## Layout thrashing
- Interleaving DOM *reads* (that force layout) and *writes* in a loop invalidates layout each iteration → forced synchronous layout ("layout thrashing"). Reads that flush: `offsetTop/Width/Height`, `clientRect`, `getComputedStyle`, `scrollTop`, `getBoundingClientRect()`, `focus()`, `innerText`.
- Fix: **batch** — read all measurements first, then write all mutations (read/write separation). Libraries: FastDOM (schedules reads then writes in rAF). Or use `IntersectionObserver`/`ResizeObserver` instead of polling geometry.
- DevTools flags forced reflow as a purple "Recalculate Style"/"Layout" with a warning triangle inside a script call.

## Compositor layers & pixel pipeline
- Layers get their own GPU texture; compositing moves/blends them cheaply. Promote a layer with `transform: translateZ(0)`/`will-change: transform`, or implicitly via 3D transforms, `<video>`, `<canvas>`, animated opacity, `position:fixed`.
- `will-change`: hints the browser to pre-promote; **overuse costs memory** (each layer = W×H×4 bytes VRAM) and can *slow* things. Add just before an animation, remove after; don't leave it on hundreds of elements or globally.
- Pixel pipeline stages the browser can skip: JS → Style → Layout → Paint → Composite. Composite-only animation skips Layout+Paint. "Paint flashing" (DevTools rendering tab) shows green repaint regions; "Layer borders" shows compositor layers.
- Layer explosion: too many layers → compositing + memory overhead; overlap can force unintended layer creation (an element above a promoted layer gets its own layer). Watch layer count in the Layers panel.

## RAIL, long tasks, INP
- RAIL budgets: **Response** ≤100ms to feel instant, **Animation** 16ms/frame (~10ms work budget after browser overhead) for 60fps, **Idle** do work in ≤50ms chunks, **Load** interactive ≤5s (or ~3.8s TTI target).
- **Long task** = main-thread task >50ms; blocks input, hurts responsiveness. TBT (Total Blocking Time) sums the >50ms overage of tasks between FCP and TTI.
- **INP** (Interaction to Next Paint, a Core Web Vital) = worst-ish (98th pct) full latency of interactions: input delay + processing + presentation delay. Good ≤200ms, poor >500ms. Optimize by: yielding to main thread (`scheduler.yield()`/`postTask`/`setTimeout(0)`), breaking long handlers, deferring non-urgent work, minimizing layout/paint after the interaction.
- Yield so the browser can paint the interaction feedback *before* heavy work: `await scheduler.yield()` mid-handler. `requestIdleCallback` for truly deferrable work (with `timeout`).

## Main-thread offloading
- Move CPU-heavy work off main thread: **Web Workers** (no DOM, message-passing, structured clone or `Transferable`/`SharedArrayBuffer` to avoid copy). OffscreenCanvas for worker-side rendering.
- Break large synchronous JS into chunks with yielding; use `content-visibility: auto` + `contain-intrinsic-size` to skip layout/paint of offscreen content. `contain: layout paint` isolates a subtree so its reflow doesn't escape.

## Memory leaks
- **Detached DOM**: node removed from document but retained by a JS reference (array, closure, framework cache) → whole subtree + listeners stay alive. Find via Memory panel → "Detached HTMLElement" in a heap snapshot.
- **Listeners**: `addEventListener` without removal on elements you discard; anonymous handlers can't be removed → keep a ref or use `AbortController` (`addEventListener(..., {signal})`, then `controller.abort()`). `{ once:true }` auto-removes.
- **Closures**: a long-lived closure capturing a large object (or the whole enclosing scope) pins it. Timers/intervals not cleared, unbounded caches/maps (use `WeakMap`/`WeakRef`/`FinalizationRegistry`), global arrays that only grow.
- Growing memory across repeated actions (comparing heap snapshots, retained size climbing) = leak; compare with the 3-snapshot technique and check the "Retainers" tree for what pins the object.

## Style, containment & isolation
- Style recalc scales with (elements × rule complexity). Deep descendant/universal selectors and huge stylesheets slow "Recalculate Style". Prefer flat, specific selectors; avoid `*` in hot subtrees.
- `contain: strict` = `layout paint size style`; tells the browser a subtree's layout/paint cannot affect the outside → scopes reflow to that box. `contain: content` (layout paint style) is the common safe choice. Enables offscreen skipping and independent invalidation.
- CSS `transform`/`opacity`/`filter` create a **stacking context**; `position:fixed`, `will-change`, `mix-blend-mode`, `isolation:isolate` too — affects paint order and layer promotion.
- `@media (prefers-reduced-motion)` to gate composited animations; respect it for accessibility + battery.

## Frame lifecycle & rAF
- Per frame the browser: runs input handlers → `requestAnimationFrame` callbacks → style → layout → paint → composite. rAF runs right before layout, so it's the correct place to batch DOM writes/animation state; measurements read here are pre-layout of THIS frame (reading geometry here forces layout of last frame's tree).
- `ResizeObserver` callbacks fire after layout, before paint, in a dedicated step — safe place to read size without thrashing. Deliver loop guards against infinite resize loops (`ResizeObserver loop limit exceeded` warning).
- `IntersectionObserver` is async + off the main critical path — use for lazy-load/visibility instead of scroll + `getBoundingClientRect`.
- Passive event listeners (`{passive:true}`) on `touchstart`/`wheel` let the compositor scroll without waiting on JS `preventDefault` → smoother scroll; non-passive scroll listeners block scrolling.

## DevTools profiling
- **Performance panel**: record → flame chart of main thread (yellow=JS, purple=layout/style, green=paint/composite). Look for long tasks (red-cornered), forced reflow warnings, dropped frames (red bar in FPS/frames track), and long "Recalculate Style"/"Layout" blocks. "Bottom-Up"/"Call Tree" to find heavy functions.
- **Memory panel**: heap snapshot (retained vs shallow size, distance, retainers), allocation timeline/sampling to catch leaks over time, "Detached" filter for orphaned DOM.
- **Rendering** drawer: Paint flashing, Layer borders, FPS meter, "Layout Shift Regions" (CLS), Core Web Vitals overlay.
- **Coverage** tab: unused CSS/JS bytes. **Lighthouse** for CWV + opportunities.

## Gotchas -> Fix
- Animating `left/top/width/height` → reflow every frame, jank → **animate `transform` (`translate`/`scale`) + `opacity` only**.
- Reading `offsetWidth`/`getBoundingClientRect` inside a write loop → forced synchronous layout thrash → **batch reads then writes; use rAF/FastDOM**.
- `will-change` left on many/all elements → VRAM blowup, slower not faster → **apply just-in-time, scope tightly, remove after animation**.
- Big non-deferred `<script>` in `<head>` → blocks parsing + first paint → **`defer`/`async`, move to end, or code-split**.
- `@import` in CSS → serialized, delays CSSOM → **use `<link>`; inline critical CSS**.
- Layout shift from images/ads without dimensions → CLS → **set `width`/`height` or `aspect-ratio`; reserve space; `font-display: optional/swap` for FOIT**.
- Long input handler blocks the paint of its own feedback → high INP → **yield with `scheduler.yield()`; defer non-urgent work; keep handler <50ms**.
- Event listeners on removed nodes / SPA route changes → detached-DOM leak → **`AbortController` signal or explicit `removeEventListener`; null out refs**.
- `setInterval`/observers not disconnected on unmount → leak + wasted work → **clear timers, `observer.disconnect()`, abort fetches in cleanup**.
- Offscreen heavy DOM still laid out/painted → wasted main-thread → **`content-visibility: auto` with `contain-intrinsic-size`**.
- Compositing many overlapping promoted layers → memory + slower composite → **reduce layer count; check Layers panel**.
- `visibility:hidden` still occupies layout/paints; assumed free → **use `display:none` to drop from render tree if geometry not needed**.
- Structured-clone of large objects to a worker copies (slow) → **use `Transferable` (ArrayBuffer) or `SharedArrayBuffer`**.
- Non-passive `wheel`/`touchstart` listener → browser must wait for JS before scrolling → scroll jank → **add `{passive:true}` unless you truly `preventDefault`**.
- Reading geometry inside a `requestAnimationFrame` callback then writing → still forces layout of the prior frame → **read in `ResizeObserver`/before the write batch, write in rAF**.
- Deep universal/descendant selectors → slow style recalc on every change → **flatten selectors; scope with `contain`**.
- Promoting a scroll container with `will-change` but leaving overflow subtree unpromoted → paints on scroll → **promote the moving layer, not everything; verify in Layers panel**.
