# Web Accessibility

## Semantic-first (before ARIA)
- First rule of ARIA: don't use ARIA if a native element does the job. `<button>` beats `<div role="button" tabindex="0" onKeyDown=...>` — free focus, Enter/Space activation, form semantics.
- Use `<nav>`, `<main>` (one per page), `<header>`, `<footer>`, `<aside>`, `<section aria-labelledby=...>` — landmarks let screen-reader users jump by region.
- Links navigate (`<a href>`), buttons act (`<button>`). An `<a>` without `href` is not focusable; a link styled as a button still announces "link".
- `<button>` inside a form defaults to `type="submit"` — set `type="button"` for non-submit actions.
- Images: `alt` describes function/content; decorative images get `alt=""` (never omit the attribute). Icon-only buttons need `aria-label` or visually-hidden text.

## Keyboard nav & focus management
- Everything mouse-usable must be keyboard-usable: Tab to reach, Enter/Space to activate, Escape to dismiss, arrows within composite widgets (menus, tabs, radios).
- Never remove focus indicators; style them: `:focus-visible { outline: 2px solid ...; outline-offset: 2px }` (`:focus-visible` skips mouse clicks).
- `tabindex="0"` adds to tab order, `tabindex="-1"` makes programmatically focusable only. Never use positive tabindex — it wrecks natural order.
- Modals: move focus into the dialog on open, trap Tab inside, restore focus to the trigger on close. Native `<dialog>.showModal()` gives focus containment, Escape, and `::backdrop` for free; pair with `inert` on the background if needed.
- SPA route change: move focus to the new page's `<h1>` (`tabindex="-1"` + `.focus()`) or announce via live region — otherwise screen readers hear nothing.
- Skip link: first focusable element, `<a href="#main">Skip to content</a>`, visually hidden until focused.

## ARIA done correctly
- ARIA changes what's announced, not how things behave — you must still implement keyboard handling yourself.
- `aria-label` / `aria-labelledby` name a thing; `aria-describedby` adds secondary info (hints, errors). `aria-labelledby` overrides visible text — beware mismatches with `aria-label` on elements with visible labels (breaks voice control; keep the accessible name starting with the visible text).
- States: `aria-expanded` (on the trigger, not the panel), `aria-pressed` (toggle buttons), `aria-current="page"` (nav), `aria-selected` (tabs/options), `aria-checked`, `aria-disabled` (still focusable, unlike `disabled`).
- `aria-hidden="true"` removes a subtree from the accessibility tree — never put it on a focusable element or its ancestor.
- Live regions: `aria-live="polite"` (or `role="status"`) for async updates like "Saved" / results counts; `role="alert"` (assertive) for errors. The region must exist in the DOM *before* content is injected.
- Tabs pattern: `role="tablist"` > `role="tab"` (with `aria-selected`, `aria-controls`) + `role="tabpanel"`; arrow keys move between tabs, Tab exits the tablist.
- `role="presentation"`/`"none"` strips semantics (e.g., layout tables); don't use on interactive elements.

## Forms, labels, errors
- Every input needs a programmatic label: `<label for="id">` or wrapping `<label>`. Placeholder is not a label (disappears on input, low contrast).
- Group related fields: `<fieldset><legend>` for radio/checkbox groups.
- Errors: link error text with `aria-describedby`, set `aria-invalid="true"`, and on submit either focus the first invalid field or focus an error-summary block listing links to fields.
- `autocomplete` tokens (`email`, `given-name`, `postal-code`) are a WCAG 2.1 AA requirement (1.3.5) and help everyone.
- Don't disable the submit button as "validation" — allow submit and show errors; disabled buttons are unfocusable and unexplainable.

## Color & contrast
- WCAG AA: 4.5:1 for normal text, 3:1 for large text (≥24px, or ≥18.66px bold) and for UI components/focus indicators/graphical objects.
- Never rely on color alone (error = red border only → add icon/text). Check link color vs body text (3:1) if links aren't underlined.
- Respect `prefers-reduced-motion: reduce` — disable parallax, auto-playing animation, large transitions.

## Screen-reader gotchas
- `display: none` and `visibility: hidden` remove content from SRs too; visually-hidden-but-readable needs the `.sr-only` clip pattern (`position:absolute; width:1px; height:1px; clip-path: inset(50%); overflow:hidden; white-space:nowrap`).
- CSS `order`/grid placement reorders visually but not for SR/tab order — keep DOM order meaningful.
- Heading levels are navigation: one `<h1>`, no skipped levels; don't pick headings for font size.
- `title` attribute is unreliable (no keyboard/touch exposure) — don't use it as the only label.

## Testing
- Automated: `axe-core` (`@axe-core/react`, `jest-axe`, `@axe-core/playwright`, Lighthouse a11y audit) catches ~30-40% of issues — contrast, missing labels, invalid ARIA.
- Manual pass: unplug the mouse (Tab through everything), zoom to 200%, run VoiceOver (Cmd+F5, macOS) or NVDA (free, Windows).
- Playwright: `new AxeBuilder({ page }).analyze()`; assert `results.violations` is empty per page state, not just on load.

## Media, motion, touch
- Video: captions (`<track kind="captions">`) for deaf users, transcripts for audio; never autoplay with sound; provide pause controls for anything moving >5s (WCAG 2.2.2).
- Touch targets: minimum 24×24 CSS px (WCAG 2.2 AA, 2.5.8); 44×44 is the comfortable standard — pad small icons, don't shrink hit areas to the glyph.
- Zoom: never set `maximum-scale=1` or `user-scalable=no` in the viewport meta; content must survive 200% zoom and 320px-wide reflow (WCAG 1.4.10) without horizontal scrolling.
- Text spacing: layouts must not break when users override line-height to 1.5 and letter/word spacing (WCAG 1.4.12) — avoid fixed-height text containers.
- Timeouts: warn and let users extend any session timeout (20x extension or disable) per WCAG 2.2.1.

## Gotchas -> Fix
- **Clickable `<div>`s**: replace with `<button>`; if impossible, add `role="button"`, `tabindex="0"`, and both Enter and Space keydown handlers (Space on keyup per native behavior, and prevent page scroll).
- **`aria-expanded` on the panel**: it belongs on the trigger button; panel gets `id` referenced by the trigger's `aria-controls`.
- **Toast appears but SR silent**: live region was injected together with the message; render an empty `role="status"` container at app start and swap its text.
- **Focus lost after deleting a list item**: focus the next/previous item or list container explicitly; browsers dump focus to `<body>`.
- **`outline: none` in a reset**: restore with `:focus-visible` styles globally.
- **Icon button announces nothing**: add `aria-label="Close"`; ensure any `svg` inside has `aria-hidden="true"` `focusable="false"`.
- **Infinite scroll traps keyboard users**: provide a "load more" button alternative and a way past the list.
- **`disabled` fields skipped by SR users reviewing a form**: prefer `aria-disabled="true"` + blocking in the handler when discoverability matters.
- **Autofocus stealing context on load**: avoid `autofocus` except single-purpose pages (search, login).
