# Web Components

## The three specs
- **Custom Elements**: define your own HTML tags with a JS class + lifecycle.
- **Shadow DOM**: encapsulated DOM + scoped CSS attached to an element.
- **HTML `<template>` + `<slot>`**: inert reusable markup + content projection.
- Native browser standard (no framework), framework-agnostic, reusable across React/Vue/Angular/vanilla. Custom tag name **must contain a hyphen** (`my-card`, never `mycard`).

## Custom elements
```js
class MyCounter extends HTMLElement {
  static observedAttributes = ['count'];        // which attrs trigger the callback
  constructor() { super(); this.attachShadow({ mode: 'open' }); }  // no DOM/attr access here
  connectedCallback()    { this.render(); }      // inserted into DOM — do setup, add listeners
  disconnectedCallback() { /* remove listeners, teardown */ }
  attributeChangedCallback(name, oldV, newV) { if (oldV !== newV) this.render(); }
  adoptedCallback()      { /* moved to a new document */ }
}
customElements.define('my-counter', MyCounter);
```
- **Lifecycle rules**: constructor may not touch attributes/children/DOM (element not upgraded/inserted yet) — defer to `connectedCallback`. `connectedCallback` can fire **multiple times** (re-insertion) → make setup idempotent, tear down in `disconnectedCallback`.
- **Upgrade**: elements parsed before their `define()` are inert then upgraded when defined; handle already-set properties with a "lazy properties" pattern (delete + reassign through the setter).
- Autonomous elements extend `HTMLElement`. Customized built-ins (`extends: 'button'`, `is="..."`) exist but are unsupported in Safari — avoid.

## Attributes vs properties (critical)
- **Attributes** are strings in HTML; **properties** are JS values on the element. They are **not** auto-synced.
- Convention: attributes for initial/primitive config (`disabled`, `count="3"`); **properties for rich data** (objects, arrays, functions) — you cannot put an object in an attribute.
- **Reflection**: mirror a property to an attribute (via setter → `setAttribute`) only for primitives you want stylable/queryable in CSS/DOM. Guard against infinite loops (attr change → prop set → attr change).
- Frameworks differ: some set attributes, some set properties — mismatches are the #1 interop bug.

## Shadow DOM & styling
- `attachShadow({ mode: 'open' })` → styles + DOM inside are **encapsulated**: outer CSS doesn't leak in, inner CSS doesn't leak out. `mode: 'closed'` hides `.shadowRoot` (rarely worth it; not a security boundary).
- Styling from outside is deliberately limited:
  - **CSS custom properties pierce** the boundary — expose theming via `var(--my-color)`; the single sanctioned styling hook.
  - **`::part(name)`**: element exposes `part="name"`; outside styles it with `my-el::part(name){}`.
  - **`:host`**, `:host(.selector)`, **`:host-context(...)`** style the element itself from inside.
  - `::slotted(selector)` styles **slotted** (light-DOM) nodes from inside the shadow (first level only).
- Inherited properties (color, font) still cross the boundary; most others don't.

## Slots (content projection)
- `<slot>` renders light-DOM children inside the shadow tree. **Default slot** + **named slots** (`<slot name="header">`, child `slot="header"`).
- Slotted nodes stay in the **light DOM** (author-stylable, in the main document) but are *displayed* at the slot position. `slotchange` event fires when assigned nodes change.

## Events
- Dispatch typed events for output: `this.dispatchEvent(new CustomEvent('change', { detail: {...}, bubbles: true, composed: true }))`.
- **`composed: true`** is required for the event to cross the shadow boundary into the light DOM; without it, bubbling stops at the shadow root.
- **Retargeting**: `event.target` is re-pointed to the host when an internal event escapes the shadow DOM (encapsulation) — use `event.composedPath()` to see the real internal origin.

## Lit
- Thin (~5KB) library over the standards: reactive properties, declarative templates, efficient updates.
```js
import { LitElement, html, css } from 'lit';
class MyBtn extends LitElement {
  static properties = { label: {}, count: { type: Number } };
  static styles = css`button { color: var(--c, blue); }`;
  render() { return html`<button @click=${this._inc}>${this.label} ${this.count}</button>`; }
  _inc() { this.count++; this.dispatchEvent(new CustomEvent('inc', { bubbles: true, composed: true })); }
}
customElements.define('my-btn', MyBtn);
```
- `@property()` (reflected/attribute-mapped, public) vs `@state()` (internal); efficient `html` tagged-template re-renders only changed bindings; `@event` binding syntax.

## Framework interop
- **React <19**: passes everything as **attributes** and doesn't listen to custom events → objects stringify, events need manual `ref` + `addEventListener`. **React 19** adds proper custom-element property/event support.
- **Vue**: works well; mark tags via `compilerOptions.isCustomElement` (or `.ce` for custom-element build) so Vue doesn't try to resolve them as components.
- **Angular**: add `CUSTOM_ELEMENTS_SCHEMA`; property/event binding works with `[prop]`/`(event)`.
- **SSR / hydration**: custom elements historically render empty on the server until JS upgrades them → FOUC/CLS.

## Accessibility & forms
- Shadow DOM breaks some ARIA: `aria-labelledby`/`for` **cannot reference IDs across** shadow boundaries. Manage `role`, `tabindex`, focus, and keyboard handling inside the component. ElementInternals + ARIAMixin (`this._internals.role`, `ariaLabel`) set semantics without leaking attributes.
- **Form-associated custom elements**: `static formAssociated = true` + `this._internals = this.attachInternals()`; call `this._internals.setFormValue(v)` to participate in `<form>` submission, `setValidity()` for constraint validation, and get `formResetCallback`/`formDisabledCallback`.

## Efficient styling: constructable stylesheets
- Share one `CSSStyleSheet` across many shadow roots instead of duplicating `<style>` per instance:
```js
const sheet = new CSSStyleSheet();
sheet.replaceSync(`:host{display:block}`);
class X extends HTMLElement { constructor(){ super(); this.attachShadow({mode:'open'}).adoptedStyleSheets=[sheet]; } }
```
- `adoptedStyleSheets` = deduped, parsed-once styles → lower memory, faster instantiation. Lit uses this under the hood. CSS `@import` and external `<link>` inside shadow DOM are slow/blocking — prefer adopted sheets or inline.

## :defined and upgrade timing
- `:defined` matches elements whose definition has registered. Hide un-upgraded custom elements to prevent FOUC: `my-el:not(:defined){visibility:hidden}`.
- `customElements.whenDefined('my-el').then(...)` awaits registration; `customElements.upgrade(node)` forces upgrade of a detached subtree.

## Declarative Shadow DOM (SSR)
- Server-render shadow DOM without JS via `<template shadowrootmode="open">…</template>` inside the host — browser attaches it during parsing. Enables real SSR/hydration for web components.
- Pair with adopted stylesheets/`<style>` inside the template so server-rendered markup is styled before hydration; libraries (Lit SSR) emit this automatically.

## Scoped registries & distribution
- **Scoped custom element registries** (`ShadowRoot` accepting its own `CustomElementRegistry`) let two versions of `<my-el>` coexist — solves the "name already defined" clash when shipping components into unknown host apps. Newer, check support.
- Guard `customElements.define` against double-registration (`if (!customElements.get('my-el'))`) when a component may be bundled by multiple consumers.
- Distribute as standard ES modules; publish with types (custom-elements-manifest `custom-elements.json`) so consumers get editor autocomplete + docs. Keep the bundle framework-free.

## When web components vs framework components
- **Web components**: cross-framework design systems, shared widgets across many apps/teams, long-lived UI that must outlive framework churn, embeddable third-party widgets, micro-frontends.
- **Framework components**: app-internal UI needing the framework's data flow, routing, ecosystem, DX, and SSR maturity. Common pattern: build the design system in Lit/web components, consume in the app framework.

## Pitfalls -> Fix
- **Styling leakage confusion** (outer CSS "should" style internals but can't) -> expose CSS custom properties + `::part`; use `:host`/`::slotted`; document theming API.
- **Attribute vs property mismatch** (object set as attribute → `[object Object]`) -> pass objects/arrays as **properties** via `ref`/binding; attributes only for primitives.
- **Events don't escape** (parent never hears the event) -> set `composed: true` (and usually `bubbles: true`) on `CustomEvent`.
- **`event.target` is the host, not the clicked child** (retargeting) -> use `event.composedPath()[0]` for the real source.
- **DOM/attr access in constructor** (undefined attrs, errors) -> move to `connectedCallback`; attach shadow in constructor only.
- **`connectedCallback` side effects duplicated** on re-insertion -> make setup idempotent, tear down in `disconnectedCallback`.
- **Property set before element upgraded** (value lost) -> lazy-properties pattern: capture, `delete`, re-set through setter after upgrade.
- **React interop** (props stringified, events unheard) -> upgrade to React 19, or wrap with a ref that sets properties + `addEventListener` (e.g. `@lit/react`).
- **Hydration FOUC/CLS** (empty until JS) -> use declarative shadow DOM for SSR; reserve space; `:defined` styling to hide until upgraded.
- **Broken ARIA across shadow boundary** (`aria-labelledby` to outside id fails) -> handle roles/focus internally with ElementInternals; keep label relationships within one root.
- **Form element ignored on submit** -> make it form-associated (`formAssociated` + `attachInternals().setFormValue()`).
- **Infinite attr↔prop reflection loop** -> in the attribute-changed handler, bail when the value is unchanged; guard the setter.
- **Global CSS reset expected to reach internals** -> it won't cross shadow DOM; ship internal base styles per component.
