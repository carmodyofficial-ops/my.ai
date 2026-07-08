# CSS Layout

## Grid
- Responsive card grid, no media queries: `display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:1rem`. Use `auto-fit` to collapse empty tracks so few items stretch to fill the row.
- Page shell with named areas: `grid-template-areas: "nav header" "nav main" "nav footer"; grid-template-columns: 220px 1fr; grid-template-rows: auto 1fr auto`.
- `minmax(0, 1fr)` instead of `1fr` when track contents (long words, `<pre>`, tables) must not blow out the track — `1fr` means `minmax(auto, 1fr)`.
- Center anything: `display:grid; place-items:center` on the parent. Two properties, works for any child size.
- Overlap items without absolute positioning: give both `grid-area: 1 / 1` and control paint order with `z-index` or source order.
- `grid-auto-flow: dense` backfills holes when items span multiple tracks (masonry-ish galleries).
- Subgrid (all modern browsers since 2023): `grid-template-rows: subgrid` on a card lets card internals (title/body/footer) align across sibling cards.
- Implicit tracks: rows created beyond your template are sized by `grid-auto-rows` (default `auto`); set `grid-auto-rows: minmax(100px, auto)` for consistent card heights.

## Flexbox
- `flex: 1` = `flex: 1 1 0%` (grow, shrink, zero basis — equal columns). `flex: auto` = `1 1 auto` (sizes proportional to content).
- Sticky footer: column flex on the page wrapper, `margin-top: auto` on the footer (auto margins absorb free space — also the cleanest "push item to the right" in a row).
- `gap` works in flexbox — stop using margin hacks between flex children.
- Wrapping equal-ish cards: `flex: 1 1 250px; ` on children + `flex-wrap: wrap` on the parent; last row items stretch (unlike grid `auto-fill`).
- `align-items` = cross axis, `justify-content` = main axis; the axes swap with `flex-direction: column`.

## Container queries
- Component-responsive: parent gets `container-type: inline-size` (optionally `container-name: card`), child rule: `@container card (min-width: 400px) { .card { flex-direction: row } }`.
- Container query units: `cqi`/`cqw` size type/spacing relative to the container, not the viewport.
- A size-container cannot size itself from its contents — `container-type: inline-size` forces `contain: layout inline-size`, so the element's width must come from outside.

## Position & stacking contexts
- `position: sticky` needs a scrollable ancestor with room to travel and an offset (`top: 0`); it sticks only within its parent's box.
- New stacking contexts are created by: positioned element with `z-index` ≠ auto, `opacity < 1`, `transform`/`filter`/`perspective`, `will-change`, `isolation: isolate`, `position: fixed/sticky`, flex/grid children with z-index. Inside a context, no child z-index can escape it.
- `transform` on an ancestor makes it the containing block for `position: fixed` descendants — fixed elements stop being viewport-fixed.
- Use `isolation: isolate` to deliberately fence a component's z-index war without magic numbers.

## Logical properties
- Write `margin-inline`, `padding-block`, `inset-inline-start`, `border-start-start-radius`, `inline-size`/`block-size` instead of left/right/top/bottom/width/height — free RTL and vertical-writing support.
- `text-align: start` / `end` replace `left`/`right` for direction-aware alignment.

## Responsive without media queries
- Fluid type/spacing: `font-size: clamp(1rem, 0.8rem + 1vw, 1.5rem)`.
- Readable measure: `max-inline-size: 65ch`.
- Sidebar that stacks when squeezed: flex wrap + `flex: 1 1 20rem` (sidebar) and `flex: 999 1 0` with `min-inline-size: 60%` (main) — "the sidebar" pattern.
- `aspect-ratio: 16 / 9` on media wrappers; no padding-top hack.
- `min()`/`max()` inline: `width: min(100%, 60rem)` for a self-capping container.

## Scroll & overflow
- Scroll snapping: container `scroll-snap-type: x mandatory; overflow-x: auto`, children `scroll-snap-align: start` — native carousels, no JS.
- `overscroll-behavior: contain` on modals/drawers stops scroll chaining to the page behind.
- `scrollbar-gutter: stable` reserves scrollbar space so layout doesn't shift when content grows past the viewport.
- `overflow: clip` clips without creating a scroll container (unlike `hidden`), so it doesn't break `position: sticky` descendants and allows `overflow-clip-margin`.
- Smooth in-page jumps: `html { scroll-behavior: smooth }`; guard with `@media (prefers-reduced-motion: no-preference)`.

## Sizing quick facts
- `box-sizing: border-box` globally (`*, *::before, *::after`) — padding/border included in declared width.
- `fit-content`, `min-content`, `max-content` are valid track sizes and widths: `width: fit-content` shrink-wraps a block without floats or inline-block.
- `flex-basis` beats `width` in flex layout; `flex-basis: content` sizes from content explicitly.
- Intrinsic ratios: prefer `aspect-ratio` + `object-fit: cover`; `object-position` controls crop focus.

## Gotchas -> Fix
- **Grid/flex item overflows its track (long text, `<pre>`, flex child won't shrink)**: min-width defaults to `auto` in grid/flex; set `min-width: 0` (or `min-inline-size: 0` / `overflow: hidden`) on the item.
- **`height: 100%` does nothing**: percentage heights need an explicit ancestor height chain; use `min-height: 100dvh` on the outer wrapper instead (`dvh`, not `vh`, to dodge mobile URL-bar jump).
- **`position: sticky` not sticking**: an ancestor has `overflow: hidden/auto/scroll` (creating a scroll container the sticky can't escape), or no offset (`top`) is set, or the parent is exactly as tall as the sticky item.
- **`z-index: 9999` has no effect**: the element is trapped in a lower stacking context (often an ancestor with `transform` or `opacity`); fix the ancestor, don't raise the number.
- **Centered text/icon looks off-center**: line-height/descender space; prefer `display:grid; place-items:center` over line-height tricks, and `text-box-trim` where supported.
- **Margins collapse unexpectedly**: adjacent vertical margins between siblings and parent/first-child collapse in normal flow; flex/grid containers and `display: flow-root` (or any padding/border) stop it.
- **Horizontal page scrollbar appears**: usually `100vw` (includes scrollbar width) or a negative-margin full-bleed; use `width: 100%` or `overflow-x: clip` on the offending section, and find culprits with `outline: 1px solid red` on `*`.
- **`justify-content: space-between` breaks with a wrapping last row**: use grid, or `gap` + `flex-start`, or padding math — space-between has no "align last row" control.
- **Absolutely positioned child positions against the page**: nearest positioned ancestor is missing; add `position: relative` to the intended parent.
- **`gap` percentage in grid resolves oddly / animation of grid tracks janky**: animate `grid-template-columns` only in browsers supporting interpolation; otherwise animate transform on children.
- **Image stretches/distorts in grid or flex**: default `align-items/justify-items: stretch`; set `object-fit: cover` on the img plus `min-width:0/min-height:0`, or `align-self: start`.
- **`auto-fit` makes one lonely card full-width**: use `auto-fill` to preserve empty tracks, or cap with `minmax(200px, 320px)`.
- **Sticky header hides anchor-jump targets**: `scroll-margin-top: 4rem` on targets (or `scroll-padding-top` on the scroll container).
- **iOS Safari 100vh too tall**: use `100dvh` / `100svh` (small viewport) instead of `100vh`.
