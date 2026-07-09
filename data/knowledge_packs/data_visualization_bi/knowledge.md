# Data Visualization & BI

## Chart selection by task + data type
- **Comparison across categories** → bar chart (horizontal if long labels; sort by value, not alphabetical). Grouped/stacked bars for sub-categories.
- **Trend over time** → line chart (continuous time); area for cumulative/part-of-whole over time. Bars for few discrete periods.
- **Part-to-whole** → stacked bar or 100% stacked; treemap for hierarchy. Pie only for ≤3–4 slices summing to 100%.
- **Distribution** → histogram, boxplot (compare groups), violin/density, ECDF. Never a single mean bar to show a distribution.
- **Relationship / correlation** → scatter (2 numeric); add trend line; bubble for a 3rd numeric; heatmap for correlation matrix.
- **Ranking** → sorted horizontal bar or dot/lollipop plot.
- **Geospatial** → choropleth (rates, normalized), symbol/dot map (counts). Normalize by population/area.
- **Flow/part transitions** → Sankey, funnel (conversion steps).
- One question per chart; pick the chart from the *question*, not the data shape.

## Encoding principles (perceptual accuracy)
- Accuracy ranking (Cleveland-McGill), most→least precise: **position > length > angle/slope > area > volume > color hue/saturation**.
- Encode the most important quantity with position/length; use color/area only for secondary or categorical dims.
- Bar charts must start the value axis at **0** (length encodes value). Line/scatter axes may be truncated to show variation — but label clearly.
- Minimize non-data ink (Tufte); maximize data-ink ratio; remove gridline clutter, 3D, drop shadows, redundant legends.
- Direct-label lines/points instead of forcing legend lookups; order legend to match visual order.
- Keep aspect ratio honest (~45° "banking" for slope readability); consistent scales across small multiples.

## Color
- **Sequential** (low→high, ordered): single-hue light→dark (e.g. viridis) — for magnitudes.
- **Diverging** (deviation around a midpoint, e.g. profit/loss): two hues with neutral center; set midpoint meaningfully (0).
- **Categorical** (qualitative): distinct hues, ≤7–8 categories; beyond that group "Other" or use small multiples.
- **Colorblind-safe** (~8% of men, deuteranopia): avoid red/green pairing; use viridis/ColorBrewer safe palettes; add redundant encoding (shape, label, pattern) so color isn't the sole channel.
- Use color intentionally: gray for context, one saturated hue to highlight. Consistent semantic mapping (red=bad/down) across a dashboard. Ensure text contrast (WCAG AA ≥4.5:1).

## Avoiding distortion
- **Truncated/zero-suppressed bar axis** → exaggerates differences. Bars start at 0; use dot plots if you must zoom.
- **Dual Y-axes** → imply spurious correlation via arbitrary scaling; prefer two aligned panels or indexing both to 100.
- **Pie overuse** → humans judge angles poorly; >4 slices unreadable; use bars for comparison.
- Consistent bin widths (histograms), consistent intervals (time axis — no missing/uneven gaps), no cherry-picked ranges.
- Aggregation hiding variance → show distribution/error bars, not just the mean. Avoid inverted axes, misleading area scaling (radius vs area), and 3D perspective.
- Show uncertainty: error bars/CIs/bands where estimates are shown.

## Dashboards
- **Layout**: most important KPI top-left (F/Z reading pattern); overview → detail top→bottom; group related metrics; align to a grid; generous whitespace.
- **Visual hierarchy**: size/position/color signal importance; ≤5–7 top-level views per screen; one primary message per view.
- **KPIs**: big number + comparison (vs target / prior period / trend sparkline). A number without a baseline is noise. Show direction + % change.
- **Interaction**: overview-first, then filter/drill-down (Shneiderman mantra); global filters, cross-filtering, tooltips for detail-on-demand.
- **Consistency**: shared color semantics, formats, date ranges, terminology across tiles.
- Purpose-fit: operational (real-time, dense, monitoring) vs analytical (exploratory, interactive) vs strategic/executive (few KPIs, high-level). Design for the audience + decision.

## BI tools + semantic layer
- **Tableau** (visual analysis, VizQL, strong ad-hoc exploration), **Power BI** (DAX measures, Microsoft/Excel ecosystem, cheap), **Looker** (LookML modeled semantic layer, governed, SQL-generating, embedded analytics). Also Metabase, Superset, Mode, Sigma.
- **Semantic/metric layer**: central governed definitions of metrics + dimensions (e.g. one canonical "active user", "revenue") so every dashboard/query agrees. Prevents metric drift + conflicting numbers across teams (LookML, dbt Semantic Layer/MetricFlow, Cube).
- Live query vs extract/import: extracts/aggregated tables are faster but staler; live is fresh but load-heavy.
- Row-level security + governance in the modeled layer, not per-report.

## Performance
- **Pre-aggregate**: query summary/rollup tables, not raw rows, at dashboard grain; push aggregation to the warehouse.
- Reduce marks: don't render 1M points — bin/sample/aggregate; overplotting also hurts readability.
- Filter early (partition pruning, indexes, `WHERE` before joins); limit high-cardinality dimensions.
- Cache/extract for hot dashboards; materialized views/incremental models (dbt); columnar warehouse (BigQuery/Snowflake/Redshift).
- Limit tiles per page + concurrent queries; lazy-load below the fold.

## Storytelling with data
- Structure: context → insight → so-what/action. One clear takeaway per chart; put the conclusion in the **title** ("Signups fell 20% after pricing change"), not a generic label.
- Annotate directly (callouts, reference lines, highlight the relevant series in color, mute the rest). Guide attention with preattentive cues (color, size).
- Sequence for a narrative (slideshow/scrollytelling) vs an exploratory dashboard — match to audience + goal.

## Accessibility
- Colorblind-safe palettes + redundant encoding (never color alone). Text/element contrast WCAG AA (≥4.5:1 text, ≥3:1 large/UI).
- Alt text / data-table fallback for screen readers; keyboard-navigable interactions; readable font sizes; avoid conveying meaning by hue only.

## Tables + small multiples
- Tables when exact values matter, mixed units, or lookup is the task; right-align numbers, consistent decimals, thousands separators, sparklines/heat cells for embedded trend. Zebra striping only for wide tables.
- **Small multiples** (trellis/faceting): repeat the same chart across categories with **shared axes + scales** → compare many groups without overplotting. Beats one crowded multi-series chart.
- Sort rows/facets by the value shown; keep a consistent panel order across the dashboard.

## Annotation + preattentive cues
- Preattentive attributes (processed pre-consciously): color, size, orientation, position, motion. Use exactly one to make the key mark pop; mute everything else to gray.
- Reference lines (target, average, prior period), shaded event bands, direct callouts on the point of interest. Annotate the *why*, not every point.
- Label units, time zone, currency, aggregation grain, and data-as-of date on every view.

## Numbers + formatting
- Round to decision-relevant precision (revenue to $, rates to 0.1%); avoid false precision. Show % change with sign + direction arrow.
- Consistent date formats (ISO or locale), consistent number scales (K/M/B), consistent color-metric mapping across the whole report.
- Handle nulls/zeros explicitly (blank ≠ 0); annotate incomplete/partial latest period.

## Interaction + drill patterns
- **Overview → zoom/filter → details-on-demand** (Shneiderman). Global filters affect all tiles; cross-filtering (click a bar → filters siblings) for exploration.
- **Drill-down** (region → country → city) via hierarchies; **drill-through** to a detail page; brushing/linking across coordinated views.
- Tooltips carry precise values + secondary context so the chart stays uncluttered. Keep default state answering the top question without any clicks.

## Metric hygiene
- Define numerator/denominator, filters, and time grain for every metric; avoid ambiguous "users" (active? unique? new?). Ratios need consistent windows.
- Distinguish snapshot vs cumulative vs period metrics; label the aggregation (sum/avg/distinct-count). Beware averaging averages (weight correctly).

## Pitfalls -> Fix
- **Truncated bar axis** (exaggerated diffs) -> start bars at 0; use dot plot to zoom.
- **Dual Y-axes implying correlation** -> separate aligned panels or index both to 100.
- **Pie/donut with many slices** -> sorted bar chart; reserve pie for ≤3–4 parts of a whole.
- **Chartjunk / 3D / heavy gridlines** -> maximize data-ink; flatten; remove decoration.
- **Rainbow / non-perceptual colormap** (jet) -> perceptually uniform sequential (viridis); diverging for signed data.
- **Red/green as sole encoding** (colorblind-inaccessible) -> colorblind-safe palette + shape/label redundancy.
- **Too many metrics per dashboard** -> ≤5–7 views; one message each; progressive drill-down.
- **KPI number with no baseline** -> add vs target / prior period / sparkline trend.
- **Encoding value with area/angle** (imprecise) -> use position/length (bar/dot).
- **Mean bar hiding distribution** -> boxplot/histogram/violin; show spread + error bars.
- **Inconsistent metric definitions across reports** -> govern in a semantic/metric layer; single source of truth.
- **Slow dashboard on raw data** -> pre-aggregate, extract/cache, filter early, reduce marks.
- **Alphabetical instead of value ordering** -> sort bars/rankings by the value shown.
- **Misleading area/bubble scaling** (radius ∝ value) -> scale by area, not radius.
- **Generic titles** -> put the insight/takeaway in the title.
