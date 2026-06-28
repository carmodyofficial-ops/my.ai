# Web Frontend (HTML / CSS / DOM)

## Semantic HTML
- Real elements, not `<div>` soup: `<button>`, `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`; they give keyboard, focus, roles free.
- One `<h1>`; nest headings in order (`h2`>`h3`), don't skip levels for size.
- Action = `<button type="button">`; navigation = `<a href>`. Never a clickable `<div>`.
- Label every control: `<label for="email">Email</label><input id="email">`. Aids a11y + SEO.

## CSS Layout
- **Flex** = 1D (toolbars, nav rows). **Grid** = 2D (page/card layouts). Use `gap`, not margins.
- `box-sizing:border-box` globally so width includes padding+border.
- Size in `rem`/`em`; `px` only for hairlines. Fluid: `clamp(1rem,2vw,2rem)`.
- Custom props: `:root{--brand:#0a6}` -> `color:var(--brand)`.
- Mobile-first `@media (min-width:48rem){...}`. Keep selectors flat; never `!important`.

## DOM
- `querySelector`/`querySelectorAll`. **Event delegation**: one listener on a parent, `e.target.closest()` finds the hit — survives dynamically added nodes.
```js
list.addEventListener('click', e => {
  const li = e.target.closest('li'); if (!li) return;
  li.classList.toggle('done');
});
```
- Build: `el=document.createElement('li'); el.textContent=name; parent.append(el);`
- `textContent` escapes (safe); `innerHTML` with user data = **XSS**. Read attrs via `el.dataset.id`. Debounce input/scroll/resize (~150ms).

## Fetch / async
- `fetch` only rejects on network failure — **404/500 do NOT throw**. Check `res.ok`.
```js
const res = await fetch(url, {signal});
if (!res.ok) throw new Error(res.status);
const data = await res.json();
```
- Wrap in try/catch for error UI. Cancel in-flight with `AbortController` (`c.signal` -> `c.abort()`).

## Forms
- Real `<form>`; read via `new FormData(form)` -> `data.get('email')`. `e.preventDefault()` then submit via fetch.
- Native `required`, `type="email"`, `minlength`. Client validation is UX only — **server must re-validate**.

## Accessibility
- Keyboard-navigable: logical focus order, visible `:focus-visible` ring (don't `outline:none`).
- `alt` on meaningful images (`alt=""` if decorative). `aria-label` on icon-only buttons.
- Prefer native elements; add ARIA only when none fits (bad ARIA < no ARIA). Contrast >= 4.5:1.

## Browser APIs
- `localStorage`/`sessionStorage`: **strings only** — `JSON.stringify`; wrap in try/catch.
- `URLSearchParams` for queries. `history.pushState({},'',url)` for SPA routing (`popstate`).
- `IntersectionObserver` for lazy-load / infinite scroll, not scroll listeners.

## Performance
- Defer JS: `<script defer src>`, never blocking in `<head>`.
- Batch DOM: **read all layout, then write all** — interleaving forces thrash.
- `loading="lazy"` on offscreen `<img>`; set `width`/`height` to avoid CLS.

## Gotchas -> fix
- `innerHTML=userInput` -> XSS; use `textContent`.
- fetch silent on 404 -> check `res.ok`.
- `div` onclick -> no keyboard/focus; use `<button>`.
- Missing `<label>` -> link `for`/`id`.
- `offsetHeight` read mid-write loop -> thrash; split read/write.
