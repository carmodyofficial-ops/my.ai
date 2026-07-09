# CSS Architecture
## Design tokens
- Define primitives (`--color-blue-500`, `--space-4`) then semantic aliases (`--color-accent: var(--color-blue-500)`, `--surface-raised`). Components consume semantic tokens, never primitives.
- Theming: swap the semantic layer under `[data-theme="dark"]`; primitives stay fixed. One source of truth → restyle without touching components.
- Token tiers: primitive (raw scale) → semantic (intent: accent, danger, surface) → component (`--button-bg`). Keep it to 2–3 tiers.
## Scales
- Type + spacing on a modular scale, not arbitrary values. Spacing: 4px base (`4,8,12,16,24,32,48`). Type: 1.2–1.25 ratio steps. Store as tokens so everything snaps to the grid.
- Fluid sizing with `clamp(min, preferred-vw, max)` for type/spacing instead of many breakpoints.
## Methodologies
- **BEM**: `block__element--modifier` — flat, low specificity, explicit. Good in plain CSS/large teams; verbose.
- **CSS Modules**: build-time hashed class names → automatic scoping, no naming discipline needed. Compose with `composes`.
- **Utility-first (Tailwind)**: atomic classes, no naming, styles co-located in markup; enforce the token scale via config. Extract repeated clusters into components, not `@apply` soup.
- **CSS-in-JS**: scoped + dynamic but runtime cost; prefer zero-runtime (vanilla-extract, Linaria) or `@scope`.
## Layered architecture (ITCSS)
- Author generic→specific so specificity rises with the cascade, not against it. ITCSS layers: Settings (tokens) → Tools (mixins) → Generic (reset) → Elements (bare tags) → Objects (layout patterns) → Components → Utilities/Trumps.
- Map directly onto `@layer reset, base, tokens, objects, components, utilities;` — the ITCSS pyramid becomes explicit cascade layers, so file order stops mattering.
## Naming
- BEM anatomy: Block = standalone (`card`), Element = child, no standalone meaning (`card__title`), Modifier = variant/state (`card--featured`, `card__title--muted`). Never chain elements (`card__body__title`) — flatten. State from data attrs/`is-`/`aria-*`, not deep modifiers.
- Utility naming: predictable, terse, value-encoding (`mt-4`, `text-center`, `flex`); one job each. Keep utilities and component classes in separate layers so authorship is unambiguous.
## Component API via custom properties
- Expose a component's knobs as CSS variables with fallbacks: `.btn{ background: var(--btn-bg, var(--color-accent)); padding: var(--btn-pad, .5rem 1rem) }`. Consumers set `--btn-bg` in context instead of overriding selectors.
- Register with `@property --btn-bg{ syntax:'<color>'; inherits:false; initial-value:transparent }` for type-safety + animatable custom props. This is the low-specificity way to theme/vary a component from the outside.
## Theming
- Multi-theme: keep primitives fixed, redefine the semantic layer per theme on `[data-theme]`/`.theme-x`. `color-scheme: light dark` + `light-dark()` for the two-way default. Scope a theme to a subtree by setting the attribute on a wrapper, not just `:root`.
- Runtime switch: toggle `data-theme` on `<html>` from JS; persist choice; because components read semantic vars, no re-render needed. Respect `prefers-color-scheme` as the default, user choice overrides.
## Fluid type & space
- `clamp(min, preferred, max)` where preferred mixes `rem`+`vw` (e.g. `clamp(1rem, .5rem + 2vw, 1.5rem)`) → smooth scaling, no breakpoints. Store as tokens (`--step-0…--step-5`) generated on a ratio (Utopia). Keep a `rem` term so it scales with user font size (accessibility) and cap with `max`.
## Container queries in architecture
- `@container` sizes a component to its container, not the viewport → truly portable components that adapt in any slot. Set `container-type: inline-size` on the parent; query `@container (min-width: 30rem)`.
- Architecture shift: components own their responsive rules; layout owns container widths. Container query units (`cqi`/`cqw`) for intrinsic sizing.
## Scoping
- Native `@scope (.card) to (.content) { ... }` limits rules to a subtree with a lower/donut boundary. Otherwise rely on CSS Modules hashing or BEM naming to avoid leakage.
- Keep selectors shallow: target one class, avoid descendant chains and element selectors that bleed.
## Cascade layers
- `@layer reset, base, tokens, components, utilities;` — declare order once at top. Later layers ALWAYS win regardless of specificity; unlayered styles beat all layers.
- Tames specificity wars: a `components` rule can't accidentally override a `utilities` rule. Third-party CSS goes in an early layer so your styles win without `!important`.
## Component variants
- Model variants as data (`data-variant="primary"`, `data-size="sm"`) styled via attribute selectors, or a variants lib (CVA, tailwind-variants) mapping props → class sets. Avoid boolean-class combinatorial explosion.
- Base + modifier composition; single source per variant dimension.
## z-index scale
- Define named tiers as tokens (`--z-base:0; --z-dropdown:1000; --z-sticky:1100; --z-overlay:1200; --z-modal:1300; --z-toast:1400`). Never hand-write `9999`. Leave gaps for insertion.
- Stacking context discipline: a new context (from `transform`, `opacity<1`, `filter`, `will-change`, `position+z-index`) traps children's z-index — a child can't escape its parent's layer. Debug elevation issues by finding the nearest stacking context, not by raising numbers.
## Critical CSS & splitting
- Inline above-the-fold critical CSS in `<head>` (blocking), lazy-load the rest (`media="print" onload` swap or `rel=preload`). Cuts render-blocking + FOUC. Per-route CSS via code-splitting (CSS Modules/vanilla-extract emit per-chunk files).
- Keep the critical set tiny (tokens + layout + first components). Automate extraction (Critical, Beasties) — hand-maintained critical CSS rots.
## Migration
- Strangler pattern: wrap legacy CSS in an early `@layer legacy` so new layered styles win without `!important`. Migrate component-by-component behind `@scope`/CSS Modules to stop new leakage.
- Add tokens first (map existing magic numbers to a scale), then refactor consumers. Freeze legacy (no new rules) while porting; lint blocks new raw values.
## Dead-CSS detection
- Build-time: PurgeCSS/Tailwind JIT scan content for used classes; CSS Modules + bundler treeshaking drop unimported. Runtime: DevTools Coverage tab flags unused bytes per page (per-route, so aggregate across flows).
- Caveat: dynamic/string-built class names evade static scanning — safelist them. Verify before deleting; coverage is per-load, not global.
## Gotchas -> Fix
- **Specificity wars**: nested overrides pile up, `!important` creep. Fix: cascade layers so order (not specificity) decides; keep selectors single-class.
- **`!important` escalation**: one important forces another. Fix: remove root cause (layers/lower specificity); reserve `!important` for utilities only.
- **Magic numbers**: hard-coded `13px`, `#3b7fd4` scattered. Fix: tokens on a scale; lint raw values.
- **Primitive leakage**: components use `--color-blue-500` directly → theming breaks. Fix: consume semantic tokens; primitives are private.
- **Global leakage**: unscoped `.title` clobbers another component. Fix: CSS Modules / BEM / `@scope`.
- **Dead CSS**: unused rules accumulate. Fix: PurgeCSS/Tailwind JIT scanning content; coverage tab in DevTools; treeshake CSS Modules.
- **Deep descendant selectors**: `.card .body .title span` — brittle, high specificity. Fix: flat single-class selectors.
- **z-index chaos**: random large numbers. Fix: a z-index token scale (`--z-dropdown`, `--z-modal`) + stacking-context discipline.
- **Breakpoint sprawl**: dozens of media queries. Fix: `clamp()` fluid values + container queries (`@container`) so components adapt to their own width, not the viewport.
- **Theme flash (FOUC)**: dark theme applied after paint. Fix: set `data-theme` from an inline blocking script before first paint.
- **Overriding utilities with components**: unpredictable winner. Fix: put utilities in the last layer so they always win intentionally.
- **Duplicated variant logic**: styles drift from component props. Fix: single variant map (CVA) as source of truth.
- **Inconsistent spacing/type**: eyeballed values. Fix: enforce token scale via lint (stylelint `scale-unlimited/declaration-strict-value`).
- **Child z-index ignored**: raising a child's z-index does nothing because an ancestor made a stacking context. Fix: raise/flatten the ancestor, or move the element (portal) out of the trapping context.
- **Unlayered third-party CSS wins**: a vendor stylesheet loaded outside layers beats all your layered rules. Fix: wrap imports in `@layer vendor` (via `@import ... layer(vendor)`).
- **Container query on the element itself**: an element can't query its own size, only an ancestor's. Fix: set `container-type` on a wrapper, query from the child.
- **`clamp()` with no `rem` term**: viewport-only fluid type ignores user zoom/font settings. Fix: include a `rem` component so it respects user preferences; always cap min/max.
- **Critical CSS drift**: hand-inlined critical block goes stale vs shipped CSS. Fix: regenerate on build; never hand-maintain.
- **Deleting "unused" dynamic classes**: coverage/PurgeCSS misses runtime-composed names. Fix: safelist dynamic patterns; confirm across all routes before removing.
- **Custom-prop API leaks internals**: exposing every private var invites brittle overrides. Fix: document a small public var set with fallbacks; keep internals unprefixed/undocumented.
- **`@property` missing `initial-value`**: non-inherited registered prop with no initial fails to register/animate. Fix: provide `syntax` + `initial-value` + `inherits`.
- **Big-bang rewrite**: full CSS rewrite stalls + regresses. Fix: incremental strangler behind `@layer legacy` + scoping, migrate per component.
