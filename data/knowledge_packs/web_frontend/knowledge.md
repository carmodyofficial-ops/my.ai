# Web Frontend (HTML / CSS / DOM)

## Semantic HTML
- Real elements, not `<div>` soup: `<button>`, `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`, `<dialog>`, `<details>`; they give keyboard, focus, and ARIA roles free.
- One `<h1>`; nest headings in order (`h2`>`h3`), don't skip levels for size — restyle with CSS.
- Action = `<button type="button">`; navigation = `<a href>`. Never a clickable `<div>`. Inside a `<form>`, a bare `<button>` defaults to `type="submit"`.
- Label every control: `<label for="email">Email</label><input id="email">` (or wrap the input in the label).

## DOM & events
- `querySelector`/`querySelectorAll` (static NodeList); build nodes with `document.createElement` + `append`; batch inserts via `DocumentFragment`.
- **Event delegation**: one listener on a parent; `e.target.closest('li')` finds the hit — survives dynamically added nodes.
```js
list.addEventListener('click', e => {
  const li = e.target.closest('li'); if (!li) return;
  li.classList.toggle('done');
});
```
- `textContent` escapes (safe); `innerHTML` with user data = **XSS**. `insertAdjacentHTML` has the same risk.
- `el.dataset.userId` <-> `data-user-id` attribute. `classList.add/remove/toggle/contains` — never string-concat `className`.
- `addEventListener(type, fn, {once:true})` auto-removes; `{passive:true}` for scroll/touch listeners. Remove listeners with the **same function reference**.
- Debounce input/resize (~150–300ms); throttle scroll; prefer `IntersectionObserver`/`ResizeObserver` over scroll/resize math.
- Custom events: `el.dispatchEvent(new CustomEvent('save', {bubbles:true, detail:{id}}))`.

## Fetch / async
- `fetch` only rejects on network failure — **404/500 do NOT throw**. Always check `res.ok`.
```js
const c = new AbortController();
const res = await fetch(url, { signal: c.signal });
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const data = await res.json();
```
- Cancel in-flight (typeahead, unmount) with `c.abort()`; aborted fetch rejects with `AbortError` — don't show it as an error.
- POST JSON: `fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})`. Sending `FormData` as body: **don't** set Content-Type manually (browser sets the multipart boundary).
- Cross-origin: CORS is enforced by the browser; server must send `Access-Control-Allow-Origin`. Cookies cross-origin need `credentials:'include'` + server `Allow-Credentials`.

## Forms
- Real `<form>` + submit handler: `form.addEventListener('submit', e => { e.preventDefault(); const data = new FormData(form); data.get('email'); })` — Enter key and screen readers work free.
- Native validation first: `required`, `type="email"`, `minlength`, `pattern`; `form.reportValidity()`; style with `:invalid`/`:user-invalid`. Client validation is UX only — **server must re-validate**.
- Checkboxes: unchecked boxes are absent from FormData; `data.getAll('tags')` for multi-value names.

## CSS layout
- **Flex** = 1D (toolbars, nav rows). **Grid** = 2D (page/card layouts). Use `gap`, not margins between siblings.
- `box-sizing: border-box` globally (`*,*::before,*::after{box-sizing:border-box}`) so width includes padding+border.
- Centering: flex parent + `align-items:center; justify-content:center`, or grid + `place-items:center`.
- Responsive grid without media queries: `grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`.
- Size in `rem`/`em`; `px` only for hairlines. Fluid type: `clamp(1rem, 2vw + 0.5rem, 1.5rem)`. Mobile viewport height: prefer `dvh` over `vh` (mobile URL bar).
- Custom props: `:root{--brand:#0a6}` -> `color:var(--brand)`; they cascade and can be overridden per-theme/media query.
- Mobile-first `@media (min-width: 48rem){...}`. Keep selectors flat and low-specificity; avoid `!important`.
- Stacking: `z-index` only works on positioned (or flex/grid-child with transform/opacity) elements, and is scoped to its **stacking context** — a parent with `transform`/`opacity<1`/`filter` traps children's z-index.

## Storage & URL state
- `localStorage`/`sessionStorage`: **strings only** — `JSON.stringify`/`parse`; wrap in try/catch (Safari private mode / quota throws). Synchronous — don't hammer in loops. Never store secrets/tokens you can avoid.
- `URLSearchParams` for query strings: `new URLSearchParams(location.search).get('q')`; build with `params.set('q',v); history.replaceState(null,'','?'+params)`.
- SPA routing: `history.pushState` + `popstate` listener; intercept link clicks.

## Accessibility
- Keyboard-navigable: logical DOM order = focus order; visible `:focus-visible` ring (never bare `outline:none`).
- `alt` on meaningful images (`alt=""` if decorative); `aria-label` on icon-only buttons; `aria-expanded`/`aria-controls` on disclosure toggles.
- Prefer native elements; add ARIA only when nothing native fits (bad ARIA is worse than none). Text contrast >= 4.5:1.
- Hide visually but keep for screen readers: `.sr-only` clip pattern; `display:none`/`hidden` hides from everyone; `aria-hidden="true"` hides from AT only.

## Performance
- `<script defer src>` (or `type="module"`, deferred by default) — never blocking in `<head>`.
- Batch DOM work: **read all layout values, then write** — interleaved `offsetHeight` reads force layout thrash. Animate `transform`/`opacity` only (compositor); not `top/left/width`.
- `loading="lazy"` on offscreen `<img>`; always set `width`/`height` (or `aspect-ratio`) to avoid CLS. `preconnect` critical origins.

## Narrower APIs worth knowing
- Native `<dialog>`: `dlg.showModal()` gives focus trap, `Esc` close, `::backdrop`; close via `<form method="dialog">` or `dlg.close(value)`.
- `IntersectionObserver` for lazy-load/infinite scroll/"in view" analytics — not scroll listeners. `MutationObserver` to react to third-party DOM changes.
- Clipboard: `await navigator.clipboard.writeText(str)` (secure context + user gesture).
- Formatting: `Intl.NumberFormat`/`Intl.DateTimeFormat`/`Intl.RelativeTimeFormat` — never hand-roll locale formatting.
- Media queries in JS: `matchMedia('(prefers-color-scheme: dark)')` + `change` listener; respect `prefers-reduced-motion` before animating.
- Smooth scroll: `el.scrollIntoView({behavior:'smooth', block:'nearest'})`; CSS `scroll-margin-top` fixes sticky-header anchor overlap.
- `structuredClone(obj)` for deep copies (handles Dates/Maps; not functions).

## Gotchas -> Fix
- **`innerHTML = userInput`** -> XSS. Fix: `textContent`, or sanitize.
- **fetch "succeeds" on 404** -> check `res.ok` before `.json()`.
- **Clickable `<div>`** -> no keyboard/focus/role. Fix: `<button>`.
- **Listener never removed** -> anonymous fn can't be removed; keep a reference or use `{once:true}`/`AbortController` signal.
- **`e.target` is a child span, not the row** -> use `e.currentTarget` or `closest()`.
- **NodeList `.map` fails** -> `querySelectorAll` returns NodeList: `[...nodes].map(...)` (it does have `forEach`).
- **Manual `Content-Type` on FormData** -> breaks multipart boundary; delete the header.
- **`z-index: 9999` ignored** -> element isn't positioned, or an ancestor created a stacking context; fix the context, not the number.
- **Layout thrash in a loop** -> split reads and writes; cache measurements.
- **Modal scroll bleed** -> `overflow:hidden` on `body` while open, or use native `<dialog>` + `showModal()`.
- **`100vh` overflows on mobile** -> use `100dvh`.
- **localStorage JSON crash** -> `JSON.parse` of `null`/corrupt value; guard with try/catch + default.
- **Date input value** -> `<input type="date">` yields `"YYYY-MM-DD"` string; `new Date(str)` parses it as **UTC** midnight — beware off-by-one-day in local time.
- **Button inside form reloads page** -> default `type="submit"`; set `type="button"` or handle `submit` with `preventDefault`.
- **Sticky element not sticking** -> ancestor with `overflow: hidden/auto` breaks `position: sticky`; also needs a `top` value.
- **Flex child won't shrink / text won't truncate** -> flex items default `min-width: auto`; set `min-w-0`/`min-width: 0` (or `overflow: hidden`) on the item.
- **Image stretches oddly in flex/grid** -> set `object-fit: cover` and constrain the box; images are inline by default (`display: block` kills baseline gap).
