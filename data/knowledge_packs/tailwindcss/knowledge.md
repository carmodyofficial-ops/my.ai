# Tailwind CSS

## Core utilities
- **Layout:** `flex` `inline-flex` `grid grid-cols-3` `gap-4` `hidden` `block`; `flex-col` `items-center` `justify-between` `flex-1` `shrink-0` `col-span-2` `place-items-center`.
- **Spacing:** padding `p-4` `px-2` `pt-1`; margin `m-auto` `mx-4`, negative `-mt-2`; between children `space-y-4` (or `gap-*` on flex/grid). Scale: `1` = 0.25rem, so `4` = 1rem.
- **Sizing:** `w-full` `w-1/2` `max-w-md` `min-h-screen` `h-10` `size-8` (w+h).
- **Typography:** `text-sm/lg/2xl` `font-medium/bold` `text-center` `leading-tight` `tracking-wide` `truncate` `whitespace-nowrap` `line-clamp-2`.
- **Color:** `text-gray-700` `bg-blue-500` `border border-gray-200` `divide-y` — shades 50–950. Opacity shorthand: `bg-black/50`.
- **Effects:** `rounded-lg` `rounded-full` `shadow-md` `ring-2 ring-blue-500` `opacity-50` `transition` `duration-200` `hover:scale-105`.

## Responsive (mobile-first, min-width)
- Unprefixed = all sizes; a prefix applies at that breakpoint **and up**: `class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4"`.
- Breakpoints: `sm` 640, `md` 768, `lg` 1024, `xl` 1280, `2xl` 1536. Style mobile with bare utilities, layer larger overrides. `md:` means ">=768px", never "medium only" — for a window use `md:max-lg:`.

## State & structural variants
- `hover:bg-blue-600` `focus:ring-2` `focus-visible:outline` `active:scale-95` `disabled:opacity-50` `dark:bg-gray-900`.
- Parent-driven: `group` on parent -> `group-hover:opacity-100` on child; sibling: `peer` + `peer-checked:block` (peer must precede the target in DOM).
- Structure: `first:` `last:` `odd:bg-gray-50` `only:`; children shorthand `divide-y` `space-y-2`. Form state: `placeholder:` `checked:` `invalid:` `required:`.
- Variants stack left-to-right: `dark:md:hover:underline`.
- Dark mode: media-based by default; class/selector strategy (`dark` class on `<html>`) — v3 `darkMode:'class'`, v4 `@custom-variant dark (&:where(.dark, .dark *));`.

## Arbitrary values & variants
- Escape the scale inline: `w-[37px]` `bg-[#1da1f2]` `top-[117px]` `grid-cols-[1fr_500px]` `text-[13px]` `max-w-[65ch]`; spaces become underscores. Arbitrary property: `[mask-type:luminance]`; arbitrary variant: `[&>li]:mt-2`, `[&:nth-child(3)]:underline`.
- CSS var values: `bg-(--brand)` (v4) / `bg-[var(--brand)]` (v3). Use brackets only when no token fits — recurring values belong in the theme.

## Config
- **v3 (`tailwind.config.js`):** `content: ['./src/**/*.{html,js,jsx,ts,tsx}']` MUST cover every file with class names — anything unscanned is missing from the build. Extend, don't replace:
```js
theme: { extend: { colors: { brand: '#1da1f2' }, spacing: { 18: '4.5rem' } } }
```
Top-level `theme.colors` **replaces** the whole palette; `theme.extend.colors` adds.
- **v4 (CSS-first):** no JS config needed — in CSS:
```css
@import "tailwindcss";
@theme { --color-brand: #1da1f2; --font-display: "Inter", sans-serif; --spacing-18: 4.5rem; }
```
Theme vars auto-generate utilities (`bg-brand`, `font-display`) and are real CSS variables at runtime. Content detection is automatic (respects .gitignore); add missed paths with `@source "../lib"`. v4 installs via `@tailwindcss/vite` plugin or `@tailwindcss/postcss` (the old `tailwindcss` PostCSS plugin name is gone).
- Custom utilities: v4 `@utility tab-4 { tab-size: 4; }`; v3 `@layer utilities {...}`.

## @apply — sparingly
```css
.btn { @apply px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600; }
```
- Fine for tiny leaf primitives (`.btn`, form inputs) and third-party markup you can't touch. Overuse recreates traditional CSS: naming churn, dead styles, and you lose co-location. Prefer extracting a **component/partial** so markup and classes stay together. In v4, `@apply` inside separate files/Vue SFC style blocks needs `@reference "../app.css";`.

## Composition patterns
- Conditional classes in JS: `clsx`/`cn` helper; merge conflicting sets with `tailwind-merge` (`twMerge('p-2', 'p-4')` -> `p-4`).
- Repeated element styles: map over data with one class string; variant props via CVA-style lookup objects rather than string-building.

## Narrower features
- Attribute-driven variants: `aria-checked:bg-blue-600`, `data-[state=open]:rotate-180`, `group-data-[open]:block` — style off component-library state attributes (Radix, Headless UI) without JS class juggling.
- Container queries: `@container` on the parent, `@md:flex` on children sizes against the **container**, not viewport (v4 built-in; v3 via `@tailwindcss/container-queries`).
- Animation: built-ins `animate-spin` `animate-pulse` `animate-bounce`; custom keyframes via theme (`--animate-*` in v4 `@theme`, `theme.extend.keyframes/animation` in v3). `motion-reduce:animate-none` for accessibility; `motion-safe:` to opt in.
- Plugins: official `@tailwindcss/typography` (`prose` classes for CMS/markdown), `@tailwindcss/forms` (sane input resets). v4 loads CSS-side: `@plugin "@tailwindcss/typography";`.
- `prefix` option namespaces every utility (`tw-flex`) for embedding in host pages; `important: true` (v3) / `@import "tailwindcss" important;` wins specificity wars with legacy CSS.
- Print/media variants: `print:hidden`, `portrait:`, `landscape:`, `motion-reduce:`, `forced-colors:`.
- Multiple themes at runtime: point theme tokens at CSS variables that a `[data-theme]` selector swaps — utilities stay static, values change.

## Gotchas -> Fix
- **Dynamic class strings are invisible**: `` `bg-${color}-500` `` is never generated — the scanner needs complete literal strings. Fix: full names in a lookup (`{red:'bg-red-500'}`) or `safelist` (v3) / `@source inline("bg-red-500")` (v4).
- **Works in dev, missing in prod (v3)**: `content` glob doesn't cover that file/package — add the path (including `node_modules` UI-lib paths if needed).
- **Class ignored though present**: a conflicting utility later in the generated CSS wins regardless of your HTML attribute order (`class="p-4 p-2"` is not "last wins") — dedupe, use `tailwind-merge`.
- **`hover:` styles stuck on mobile**: touch devices — v4 gates hover on devices that support it; design tap states with `active:` too.
- **`peer-*` not applying**: `peer` element must come **before** the styled sibling; both must share a parent.
- **`space-y-*` breaks with reversed/absolute children**: use `flex flex-col gap-*` instead.
- **Dark mode toggle does nothing**: strategy is media-based by default — configure class strategy and actually toggle `dark` on `<html>`.
- **`@apply` with unknown class errors at build**: class doesn't exist in that context (typo, plugin not loaded, or v4 missing `@reference`).
- **Specificity fights with legacy CSS**: utilities are single-class, low specificity — an old `#app .card p` rule beats them. Lower legacy specificity, or `!` important modifier (`!mt-0` v3, `mt-0!` v4) as last resort.
- **Arbitrary value with spaces fails**: use underscores: `grid-cols-[200px_1fr]`.
- **v3 -> v4 upgrade surprises**: config moves to CSS `@theme`; `bg-opacity-*` utilities replaced by `/50` syntax; default border color is now `currentColor` (was gray-200) — set it explicitly; run `npx @tailwindcss/upgrade`.
- **Missing base-style resets**: Preflight unstyles `h1`/`ul`/`button` on purpose — re-add via your own base layer or the typography plugin (`prose`) for CMS content.
- **`h-screen` overflows on mobile**: URL bar; use `h-dvh` (v4) or `min-h-dvh`.
- **`truncate` not truncating**: parent must constrain width — flex items need `min-w-0` on the item.
- **Editor shows no completions**: install the official Tailwind CSS IntelliSense extension; for `clsx`/`cva` string args, configure `classAttributes`/`classFunctions` so those literals get completion + linting.
- **Gradient text**: `bg-gradient-to-r from-pink-500 to-violet-500 bg-clip-text text-transparent` (v4 spells it `bg-linear-to-r`).
- **Focus ring invisible on custom buttons**: Preflight removes little; you removed the outline — use `focus-visible:ring-2 focus-visible:ring-offset-2` instead of `focus:outline-none` alone.
- **Group variants leak into nested groups**: name them — `group/item` on the inner parent, `group-hover/item:visible` on the child.
