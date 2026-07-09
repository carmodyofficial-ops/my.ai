# Web Animations
## Transitions vs keyframes
- `transition`: interpolate a property between two states on change (hover/class toggle). One-shot, needs a trigger. `transition: transform .2s ease-out`.
- `@keyframes` + `animation`: multi-step, looping, autonomous. Control with `animation-iteration-count`, `-direction`, `-fill-mode: forwards` (hold end state), `-delay`.
- Only animate interpolatable properties; `display` can't tween (use `@starting-style` + `transition-behavior: allow-discrete` for enter/exit).
## Compositor-only props
- Animate `transform` and `opacity` only — they run on the GPU compositor, skipping layout + paint. Cheap, 60fps.
- Animating `width/height/top/left/margin` triggers layout (reflow) every frame = jank. Use `transform: translate()/scale()` instead of position/size; `filter` is composited-ish but costs paint.
- `will-change: transform` promotes an element to its own layer BEFORE animating — set shortly before, remove after. Overuse (many layers) blows GPU memory. `translateZ(0)`/`translate3d` is the old hack.
## Performance budget
- Target 60fps = ~16.7ms/frame (120Hz = 8.3ms). Stay on the compositor: only `transform`/`opacity` skip layout+paint. Everything else costs.
- Budget layers: each promoted layer uses GPU memory; dozens on mobile = crash/scroll jank. Profile in DevTools Performance (dropped frames) + Layers panel.
## FLIP
- First, Last, Invert, Play: measure start rect (First) → apply end state + measure (Last) → set an inverting `transform` so it visually stays at First → remove transform on next frame with a transition to Play. Animates expensive layout changes (list reorder, shared-element) using only cheap `transform`.
- Steps: `first = el.getBoundingClientRect()` → mutate DOM/classes → `last = el.getBoundingClientRect()` → `el.style.transform = translate(first.left-last.left, first.top-last.top)` (+scale) → force reflow → `requestAnimationFrame(() => { el.style.transition='transform .3s'; el.style.transform='' })`. Read all firsts before writing (batch) to avoid layout thrash.
## Orchestration
- Stagger: offset each child's `animation-delay`/`transition-delay` by index (`--i * 40ms`) for cascade reveals. Framer Motion `staggerChildren`, GSAP `stagger`.
- Sequence: chain via `Animation.finished` promises, WAAPI, or a GSAP timeline (`.to().to()`) — declarative offsets beat nested `setTimeout`.
## Spring vs easing
- Easing (`cubic-bezier`/`ease-out`) = fixed duration + curve; predictable, good for UI states. Spring = physics (stiffness/damping/mass), duration emergent; natural for gestures/interruptible motion (Framer Motion `type:'spring'`, iOS-like).
- Interruptible: springs re-target from current velocity smoothly; duration-based tweens snap/restart. Prefer springs for drag-release.
## Scroll-driven & View Transitions
- Scroll: `animation-timeline: scroll(root block)` ties progress to scroll position; `view()` ties to an element entering/leaving the viewport (`animation-range: entry`/`cover`/`exit`). Off main thread, no listeners. Feature-detect (`CSS.supports('animation-timeline: scroll()')`), fall back to IntersectionObserver.
- View Transitions API: `document.startViewTransition(() => updateDOM())` cross-fades old→new snapshots; name shared elements `view-transition-name` for morph. SPA in-page + cross-document (MPA) via `@view-transition{navigation:auto}`. Customize with `::view-transition-*` pseudos. Auto-skipped under reduced-motion.
## SVG & path
- Animate `stroke-dashoffset` (with `stroke-dasharray` = path length) for line-drawing. `offset-path`/`offset-distance` moves an element along a path. `<animateMotion>`/SMIL is legacy — prefer CSS/WAAPI/GSAP.
- SVG morphing (differing path shapes) needs a lib (GSAP MorphSVG, Flubber) — CSS can't tween arbitrary `d`.
## Library tradeoffs
- CSS/WAAPI: zero-dep, compositor-native — simple states, hovers, reveals. WAAPI adds JS control (play/pause/reverse, `.finished`).
- Framer Motion (React): declarative `motion.*`, auto-FLIP `layout`, `AnimatePresence` exits, springs, gestures. Reach for React component transitions.
- GSAP: framework-agnostic timelines, scrubbing, ScrollTrigger, SVG morph, broad browser support — richest choreography.
- Rule: CSS first, WAAPI for control, a lib only for orchestration/gestures/scroll scenes you'd otherwise hand-roll.
## Web Animations API
- `element.animate(keyframes, options)` returns an `Animation` — `.play()/.pause()/.reverse()/.cancel()`, `.finished` promise, `playbackRate`. Same compositor rules apply.
- Prefer WAAPI over JS `requestAnimationFrame` tweening (offloads to compositor); use rAF only for canvas/physics/scroll-linked custom logic.
## Scroll-driven
- Native `animation-timeline: scroll()` / `view()` ties animation progress to scroll/element visibility — runs off main thread, no scroll listeners. Pair with `@keyframes`. Feature-detect; fall back to IntersectionObserver.
- Avoid `scroll` event + reading layout per frame (jank); use IntersectionObserver for reveal triggers.
## Libraries — when
- CSS/WAAPI: simple UI states, hovers, reveals — no dependency.
- Framer Motion (React): declarative `motion.*`, layout animations (auto FLIP via `layout` prop), gestures, `AnimatePresence` for exit. Reach for orchestrated component transitions.
- GSAP: complex timelines, sequencing, scrubbing, cross-browser edge cases, SVG morphing. Best for rich choreography; ScrollTrigger for scroll scenes.
## Accessibility
- Respect `@media (prefers-reduced-motion: reduce)`: kill/shorten large motion, keep essential feedback. In JS check `matchMedia('(prefers-reduced-motion: reduce)').matches`.
- Vestibular triggers: large parallax, spin, zoom, and sudden scale — disable/replace with a fade under reduced-motion, don't just shorten. Default-safe pattern: author no-motion base, add motion inside `@media (prefers-reduced-motion: no-preference)`.
- Avoid flashing >3/sec (seizure risk). Ensure animated content doesn't remove focus outlines or trap keyboard focus; pause looping/auto-playing motion controls if >5s.
## Gotchas -> Fix
- **Layout thrash / jank**: animating layout props or interleaving reads (`offsetWidth`) and writes forces synchronous reflow each frame. Fix: animate `transform`/`opacity`; batch DOM reads then writes; use FLIP for layout changes.
- **`will-change` left on**: permanent extra layers eat GPU memory, can *worsen* perf. Fix: add just before, remove after animation.
- **Animating `height:auto`**: `auto` isn't interpolatable → no transition. Fix: animate `max-height`, `transform: scaleY`, or grid `grid-template-rows: 0fr→1fr`, or `calc-size()`/discrete transitions.
- **Enter animation on mount doesn't fire**: element inserted at final state. Fix: `@starting-style`, or force reflow / next frame before adding the active class.
- **`animation-fill-mode` missing**: element snaps back after animation. Fix: `forwards` to retain the end frame.
- **Ignoring reduced-motion**: triggers vestibular discomfort. Fix: gate parallax/large motion behind the media query.
- **Janky scroll listeners**: `scroll` handler doing layout/animation. Fix: `animation-timeline` or IntersectionObserver; throttle + rAF if you must.
- **Too many composited layers**: memory blowup, especially mobile. Fix: limit promoted layers; profile in DevTools Layers/Performance.
- **Framer Motion re-renders**: animating via React state each frame re-renders. Fix: use motion values / `animate()`, not `useState` per frame.
- **Transform origin surprises**: scale/rotate pivot from center by default. Fix: set `transform-origin` explicitly.
- **`transition: all`**: animates unintended properties + costs perf. Fix: list exact properties.
- **View Transition captures the whole page**: default snapshot animates everything, causing flashes. Fix: scope with `view-transition-name` on the elements that should morph; keep DOM update inside the callback synchronous.
- **Duplicate `view-transition-name`**: two live elements share a name → the transition throws/skips. Fix: names must be unique among rendered elements at capture time.
- **rAF loop keeps running off-screen**: wastes battery/main thread. Fix: pause on `visibilitychange`/IntersectionObserver; cancel `requestAnimationFrame`.
- **Compositor animation forced to main thread**: adding a non-composited property (e.g. `box-shadow`) to a `transform` animation demotes it. Fix: animate a pseudo/opacity layer for shadows; keep transform/opacity pure.
- **Scroll timeline with no fallback**: unsupported browsers show no animation. Fix: `CSS.supports` detect + IntersectionObserver fallback.
- **Staggered delays block interaction**: long cumulative `animation-delay` leaves UI unusable. Fix: cap total stagger; keep interactive elements clickable during entrance.
- **Spring never settles / overshoots layout**: under-damped spring on layout-affecting property. Fix: constrain to transform/opacity; tune damping; clamp.
