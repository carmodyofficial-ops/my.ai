# Visual Design Fundamentals

## Layout, grids, alignment
- Use a grid (columns + gutters + margins) to create structure and rhythm; 12-column is a common flexible base.
- Align everything to the grid; every element should have a deliberate edge relationship with another — no random placement.
- Strong alignment (usually left-edge for text) creates an invisible line that organizes the eye; mixed alignment reads as sloppy.
- Consistent margins/padding; give content a max line-width and breathing room.
- Establish clear content zones (header, primary, secondary, footer) with consistent structure across pages.

## Visual hierarchy (control the order the eye reads)
- Rank elements by importance, then make the ranking visible through **size, weight, color, contrast, and space**.
- Bigger, bolder, higher-contrast, more-isolated = more important. Establish a clear #1 focal point per screen.
- Contrast is the primary tool: if everything is emphasized, nothing is.
- Reading patterns: F-pattern for text-heavy pages, Z-pattern for sparse/landing layouts — place key elements along the path.
- Use position (top/left = seen first in LTR) and whitespace to signal priority.

## Typography
- Limit to 1–2 typefaces (e.g., one for headings, one for body); a single well-chosen family with multiple weights often suffices.
- **Pairing**: contrast + harmony — e.g., a serif heading with a sans body; avoid two similar-but-different fonts (clash).
- **Type scale**: use a consistent modular scale (e.g., ratio ~1.25 major third or 1.333) for step sizes, not arbitrary numbers.
- **Line-height (leading)**: ~1.4–1.6 for body text; tighter for large headings.
- **Measure (line length)**: ~45–75 characters per line for readability; too long tires the eye, too short breaks rhythm.
- Establish hierarchy with size + weight + color, not many fonts.
- Left-align body text; adequate contrast; avoid all-caps for long text; limit italics/bold to emphasis.

## Color theory
- **Color wheel** relationships (harmonies): complementary (opposite, high tension), analogous (adjacent, calm), triadic (evenly spaced, vibrant balance), monochromatic (one hue, varied value/saturation).
- **HSB/HSL** thinking: adjust hue, saturation, brightness/value independently; control value to control contrast.
- **60-30-10 rule**: ~60% dominant/neutral, 30% secondary, 10% accent — keeps palettes balanced.
- Use a restrained palette: neutrals + one or two accents; reserve a saturated accent for calls-to-action.
- **Contrast for accessibility**: text ≥ 4.5:1 (normal), 3:1 (large/UI); never rely on color alone to convey meaning.
- Consider color meaning/culture and color-blindness (avoid red/green as the only distinction).

## Spacing + white space
- White space (negative space) is an active design element — it groups, separates, and creates focus, not "empty waste".
- Use a consistent spacing scale (e.g., 4/8px system: 4, 8, 16, 24, 32…) for all margins/padding.
- **Proximity via spacing**: space between groups > space within a group, so relationships read automatically.
- Generous macro whitespace (around blocks) signals quality and reduces clutter; micro whitespace (line/letter) aids legibility.

## Gestalt principles (how the eye groups things)
- **Proximity**: elements close together are perceived as related — spacing does grouping for free.
- **Similarity**: elements sharing color/shape/size read as a set.
- **Closure**: the mind completes incomplete shapes (enables minimal icons/logos).
- **Continuity**: the eye follows lines/curves; aligned elements read as connected.
- **Common region**: a shared boundary (card, box) groups items.
- **Figure/ground**: foreground vs background separation; ensure the subject is clearly distinct.
- **Common fate**: things moving together are grouped (animation).

## Consistency + design systems
- Reuse consistent components, spacing, type, and color everywhere — consistency reduces cognitive load and builds trust.
- Codify decisions as **design tokens** (color, spacing, type, radius) and a component library / style guide.
- Establish patterns for states (default/hover/active/disabled/error) and apply them uniformly.
- Internal consistency (within product) and external consistency (platform conventions) both matter.

## Imagery + iconography
- Use a single consistent icon set (same style, stroke weight, grid); don't mix filled + outline + skeuomorphic randomly.
- Icons support recognition — pair with labels for clarity; icon-only is ambiguous.
- Images: high quality, consistent treatment (aspect ratio, filter, tone); optimize file size; provide alt text.
- Maintain visual consistency between illustrations, photos, and icons.

## Balance + emphasis
- **Balance**: distribute visual weight — symmetrical (formal, stable) or asymmetrical (dynamic, uses size/color/space to counterweight).
- **Emphasis**: one clear focal point via contrast/size/color/isolation; guide the eye deliberately.
- **Rhythm/repetition**: repeated elements create pattern and unifies a layout.
- **Alignment + proximity + repetition + contrast** (CRAP) are the four workhorse principles.

## Pitfalls -> Fix
- Too many fonts/typefaces -> Limit to 1–2 families; build hierarchy with weight/size/color instead.
- Poor/low contrast (text on background) -> Meet WCAG ratios (4.5:1); test with a contrast checker; control value.
- Inconsistent spacing (random margins) -> Adopt a spacing scale (4/8px); reuse tokens everywhere.
- Center-aligned body text -> Left-align body copy; reserve centering for short headings/single lines.
- No clear hierarchy (everything same size) -> Establish one focal point; vary size/weight/contrast by importance.
- Cramped, cluttered layout -> Add white space; group with proximity; remove non-essential elements.
- Misalignment / off-grid elements -> Align to a grid; give every element an intentional edge relationship.
- Rainbow palette / clashing colors -> Restrain palette; 60-30-10; neutrals + limited accents; use color harmonies.
- Color as the only signal -> Add text/icon/pattern; support color-blind users.
- Mixed icon styles -> One consistent icon set; uniform stroke/style.
- Lines too long/short -> Set measure to ~45–75 chars; adjust container width/font size.
- Tight/loose line-height -> ~1.4–1.6 for body; tighter for big headings.
- Arbitrary font sizes -> Use a modular type scale for consistent steps.
- Reinventing every screen -> Build a design system/component library; reuse patterns and states.
- Overusing bold/caps/italics -> Emphasize sparingly; one emphasis method at a time.
- Low-quality/inconsistent imagery -> Consistent treatment, aspect ratios, and quality; optimize + alt text.

## Contrast, value, and depth
- **Value** (light/dark) contrast is what creates legibility and hierarchy — test designs in grayscale to check it holds without color.
- Establish depth with layering cues: shadow, elevation, overlap, blur — used consistently, not decoratively.
- Contrast tools beyond color: size contrast, weight contrast, shape contrast, and spatial contrast (dense vs. open).
- Keep enough figure/ground separation that primary content never fights the background.

## Responsive + adaptive visuals
- Design at multiple breakpoints; layouts reflow (stack columns) rather than scale down uncritically.
- Type scale and spacing should adjust per viewport; don't ship desktop leading on mobile.
- Fluid grids + relative units (rem/%, not fixed px) so layout adapts.
- Prioritize content order for small screens; the most important element stays first.

## Motion + microinteractions
- Motion should clarify (state change, spatial relationship, feedback), never decorate for its own sake.
- Keep durations short (~150–300ms for UI transitions); ease-in-out for natural feel.
- Consistent motion language across the product; respect `prefers-reduced-motion`.
- Microinteractions (hover, toggle, success checkmark) confirm actions and add polish when subtle.

## Data + tables visual treatment
- Reduce chartjunk: strip gridlines, borders, and 3D effects that don't encode data.
- Align numbers right, text left; use whitespace and subtle zebra/row separation over heavy borders.
- Emphasize the data, mute the scaffolding (axes, labels in low-contrast neutral).
- Use color to encode meaning purposefully, with a colorblind-safe, accessible palette.

## Practical workflow
- Start with structure (grayscale layout + hierarchy), add type, add color last — proves the design works on bones alone.
- Build and reuse a small kit: type scale, spacing scale, color palette, component states.
- Steal proven patterns and constrain choices; originality lives in content, not in reinventing a button.

## Heuristics
- If everything stands out, nothing does — pick one focal point.
- White space is not wasted space; it does the grouping and focusing.
- Constrain choices: one grid, one spacing scale, one type scale, two fonts, a small palette.
- Alignment, contrast, proximity, repetition (CRAP) fix most amateur layouts.
- Squint at the screen: the most prominent thing should be the most important thing.
