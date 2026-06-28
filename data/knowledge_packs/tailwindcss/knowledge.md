# Tailwind CSS Reference

## Philosophy
Utility-first: compose tiny single-purpose classes in markup instead of writing custom CSS. Style without leaving HTML; no naming, no separate stylesheet churn. Reach for custom CSS only for the rare case utilities can't express.

## Core utilities
- **Layout:** `flex` `inline-flex` `grid grid-cols-3` `gap-4` `block` `inline-block` `hidden`; `flex-col` `items-center` `justify-between` `col-span-2`.
- **Spacing:** padding `p-4` `px-2` `pt-1`; margin `m-auto` `mx-4` `-mt-2`; gaps between children `space-x-2` `space-y-4`. Scale: `4` = 1rem.
- **Sizing:** `w-full` `w-1/2` `h-screen` `min-h-screen` `max-w-md` `size-8`.
- **Typography:** `text-lg` `font-bold` `text-center` `leading-tight` `tracking-wide` `uppercase` `truncate`.
- **Color:** `text-gray-700` `bg-blue-500` `border` `border-gray-200` (numeric shade 50-950).
- **Borders/effects:** `rounded-lg` `rounded-full` `shadow` `shadow-md` `ring-2` `opacity-50`.

## Responsive (mobile-first, min-width)
Unprefixed = all sizes. A prefix applies at that breakpoint **and up**.
```html
<div class="grid grid-cols-1 md:flex lg:grid-cols-4">
```
Breakpoints: `sm`640 `md`768 `lg`1024 `xl`1280 `2xl`1536. Style mobile with bare utilities, then layer larger overrides. There is no max-width default prefix—don't use `md:` for "phones only".

## State variants
Prefix to gate on state: `hover:bg-blue-600` `focus:ring` `active:scale-95` `disabled:opacity-50` `dark:bg-gray-900`. Parent-driven: add `group` to parent, `group-hover:text-white` on child (`peer` + `peer-checked:` for siblings). Variants stack: `md:hover:underline`.

## Arbitrary values
Escape the design system inline: `w-[37px]` `bg-[#1da1f2]` `top-[117px]` `grid-cols-[1fr_500px]` `text-[13px]`. Use brackets only when no scale token fits.

## @apply (sparingly)
Extract a repeated utility set into one class:
```css
.btn { @apply px-4 py-2 rounded-lg bg-blue-500 text-white; }
```
Don't wrap every element—overusing `@apply` recreates traditional CSS and loses the utility benefits. Prefer component loops/partials instead.

## Config (`tailwind.config.js`)
```js
module.exports = {
  content: ['./src/**/*.{html,js,jsx,ts,tsx}'],
  theme: { extend: {
    colors: { brand: '#1da1f2' },
    spacing: { 18: '4.5rem' },
    fontFamily: { sans: ['Inter','sans-serif'] },
  }},
}
```
Use `theme.extend` to **add** without dropping defaults; top-level `theme` keys **replace** them. `content` globs MUST list every template path or those classes get purged from the build.

## JIT
The engine scans `content` files and generates only the classes it finds, on demand—any arbitrary value works instantly, builds stay tiny.

## Gotchas -> fixes
- **Classes work in dev, missing in prod:** `content` doesn't cover the file -> add the path.
- **Dynamically built class strings** (`` `bg-${c}-500` ``) aren't detected -> use full literal class names or add them to `safelist`.
- **`@apply` everywhere:** defeats utility-first -> keep markup utilities.
- **Specificity surprises:** utilities are flat/equal-weight; rely on source order, not nesting.
- **Forgot responsive is min-width:** `md:` means >=768px, not "only medium".
