# Procedural Generation

## Seeded RNG Discipline
- Never use the global RNG (`Math.random`) for generation — unseedable, unreproducible. Use a seedable PRNG (mulberry32, xoshiro, PCG).
- One seed -> derive independent sub-seeds per system (terrain, loot, enemies) via hash: `rngLoot = prng(hash(seed, "loot"))`. Otherwise adding one terrain call reshuffles all loot ("RNG call-order coupling").
- Log the seed on every generation; a bug report without the seed is unreproducible.
- Hash coordinates for position-based randomness (`hash(seed,x,y)`) instead of sequential draws — order-independent, works for infinite/chunked worlds.
```js
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;
 let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;
 return ((t^t>>>14)>>>0)/4294967296;}}
```

## Noise (Perlin/Simplex) for Terrain
- Gradient noise returns smooth values (~-1..1) per coordinate; sample with a frequency: `noise(x*freq, y*freq)`. Higher freq = smaller features.
- Octaves (fBm): sum layers, each doubling frequency (lacunarity ~2) and halving amplitude (persistence ~0.5). 4–6 octaves = natural terrain; 1 octave = blobby.
- Shape the output: `height = pow(n*0.5+0.5, e)` — e>1 flattens lowlands into plains, sharpens peaks.
- Domain warping (`noise(x + noise(x,y)*k, y)`) breaks the uniform look cheaply.
- Biomes: two independent noise fields (moisture, temperature) -> lookup table; beats one field with thresholds.
- Simplex over classic Perlin when directional grid artifacts show. Noise is NOT random per-sample — nearby samples correlate; that's the point.

## Cellular Automata Caves
- Init grid: each cell wall with p≈0.45 (seeded). Iterate 4–5 times: cell becomes wall if ≥5 of its 8 neighbors are walls (treat out-of-bounds as wall).
- Post-pass: flood fill regions; keep the largest, fill or tunnel-connect the rest — CA routinely produces disconnected pockets.
- Tune p and iterations together: p=0.40 open caverns, p=0.48 tight tunnels.

## Dungeon Generation
- **BSP**: recursively split space (random axis, split 0.3–0.7 of span, stop at min size), place a room inside each leaf, connect sibling rooms up the tree — guarantees full connectivity by construction.
- **Rooms + corridors**: scatter non-overlapping rects (reject or nudge on overlap), connect with L-shaped corridors between room centers, ordered by nearest-neighbor or MST for a clean layout; add 10–15% extra edges for loops (pure trees feel like mazes).
- Place content by graph distance from entrance: keys before locks, boss farthest, loot density scaled by depth.

## Wave Function Collapse (concept)
- Tile-constraint solver: every cell starts as "all tiles possible"; repeatedly pick the lowest-entropy cell, collapse it to one tile (weighted), propagate adjacency constraints to neighbors.
- Contradictions (a cell with zero options) happen: restart with a new seed or backtrack. Restart is simpler and usually fine for small grids.
- Adjacency rules from a hand-made example ("overlapping" model) or explicit tile socket lists. Great for local coherence; it does NOT guarantee global properties (connectivity, reachability) — validate after.

## Loot Tables
- Weighted table: entries `{item, weight}`; roll `r = rng() * totalWeight`, walk entries subtracting. Weights are relative, not percentages — adding an entry dilutes all others.
- Nested tables (table entries can be tables) keep tuning sane: `chest -> [common(70), rare(25), epic(5)]`, each a sub-table.
- Pity/bad-luck protection: increment rare chance per miss, reset on hit — pure independence produces brutal droughts (1% item: ~36.6% of players see nothing in 100 rolls).
- Roll count and table choice should come from the content's seeded RNG stream so loot is reproducible per seed.

## Validating Generated Content
- Always validate; generators produce garbage at the tails. Checks: connectivity (flood fill from spawn reaches exit and all required content), min/max walkable area, required placements present, no overlaps.
- Reject-and-retry with a retry cap; on cap, fall back to a known-good template. Log rejection reasons — a 40% rejection rate means fix the generator, not raise the cap.
- Difficulty validation: path length spawn->exit within bounds, enemy density per region within band.
- Fuzz your generator in CI: run 1,000 seeds, assert invariants; store failing seeds as regression tests.

## Mixing Authored + Generated
- Pure procgen reads as samey after ~an hour; the fix is authored anchors: hand-made setpiece rooms/vaults stamped into generated layouts (roguelike "prefabs"), generated connective tissue between them.
- Constrain, don't just randomize: generate 20 candidates, score them (openness, path length, feature variety), keep the best — selection is the cheapest quality lever in procgen.
- Name things from seeded syllable tables and reuse palettes/motifs per region so generated areas feel intentional.

## Difficulty & Pacing in Generated Content
- Budget-based spawning: each region gets a danger budget by depth; enemies cost budget by threat — prevents both empty and impossible rooms from raw randomness.
- Guarantee the floor plan of fun: at least one reward per N rooms, a breather room after the boss, resources proportional to expected damage taken. Randomize within guardrails, never the guardrails.

## Determinism Across Platforms
- Avoid trig/transcendental float functions in generation if cross-platform reproducibility matters — implementations differ in last bits; integer hashing and fixed-point stay bit-identical.
- Iterate collections in defined order during generation (sorted keys, arrays) — hash-map iteration order differences silently fork worlds between runs/platforms.

## Gotchas -> Fix
- **Same map every run / different map per run (unwanted)**: unseeded RNG somewhere (shuffle util, engine random). Fix: audit all randomness routes through the seeded PRNG; ban `Math.random` via lint.
- **One extra RNG call reshuffles the whole world**: single shared stream. Fix: per-system sub-seeded streams; position-hashed randomness for world features.
- **Noise terrain looks like smooth blobs**: single octave, wrong frequency. Fix: fBm with 4+ octaves; tune frequency to feature size in world units.
- **Visible grid-aligned ridges in terrain**: classic Perlin axis artifacts. Fix: simplex/OpenSimplex, or rotate the sample domain.
- **CA caves have sealed-off rooms**: no connectivity pass. Fix: flood fill + keep-largest or dig connectors.
- **WFC hangs or contradicts constantly**: over-constrained tile rules. Fix: add wildcard/transition tiles, loosen adjacency, restart on contradiction with retry cap.
- **Player spawns inside a wall**: placement ignores generated geometry. Fix: placement only on validated walkable cells; assert in the validation pass.
- **Loot "percentages" stopped adding up**: someone treated weights as %, then added items. Fix: weights are relative by design; display computed probabilities in a debug view.
- **Chunk borders visibly seam**: per-chunk RNG or noise offset mismatch. Fix: noise/hash in global world coordinates, never chunk-local coordinates.
- **Generator works in dev, breaks rarely in prod**: tail-case seeds. Fix: 1,000-seed fuzz in CI; keep failing seeds as fixtures.
