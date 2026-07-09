# Level Design
## Core Principles
- Pacing: alternate tension and release (peaks and valleys) — combat then calm, tight corridor then open vista. Sustained intensity fatigues; sustained calm bores.
- Tension curve: ramp difficulty/stakes over a level toward a climax (miniboss/setpiece), then a short denouement. Map beats on a graph before building.
- Gating: block progress until a condition is met (key, ability, switch) to control sequence and teach before testing. Soft gates (difficulty, hints) vs hard gates (locked door).
- Breadcrumbing: lead the player forward with a trail of interest — collectibles, light, NPC voice, a visible objective — so they always know where to go next.
- Teach -> test -> twist (Nintendo pattern): introduce a mechanic safely, test it, then combine/subvert it. One new idea at a time.
## Blockout / Greybox First
- Build in untextured primitives (greybox/whitebox) to validate layout, scale, sightlines, and flow before any art. Cheap to change; art commits you.
- Lock metrics early: player height, jump height/distance, step height, cover height, door width, cover-to-cover distances. Build a metrics reference kit and reuse it everywhere.
- Playtest the blockout for pacing and navigation before art pass. Fixing flow in a textured level is expensive.
- Use consistent grid units; snap geometry so pieces align and modular art fits later.
## Guiding the Player
- Light: players move toward light and bright areas; use it to mark paths, exits, objectives. Darkness reads as "not here / danger".
- Lines & leading geometry: corridors, railings, architecture, rivers point toward the goal. Composition draws the eye like a photograph.
- Landmarks: a distant tower/mountain/structure gives orientation and a long-term goal (weenie, Disney term). Aids mental mapping and prevents "lost".
- Color & contrast: make interactables/paths pop against the environment (yellow ledges, colored doors). Consistency = a visual language the player learns.
- Affordance: shape signals function — ledges look climbable, cover looks like cover. Framing (doorways, arches) frames the objective.
## Encounter / Challenge Design
- Design arenas around mechanics: cover placement, sightlines, flanking routes, verticality, chokepoints, escape routes. Avoid flat symmetric boxes.
- Enemy composition and placement drive difficulty more than raw numbers: mix roles (rusher, ranged, tank), stagger spawns, use the space.
- Give readable telegraphs and reaction windows; the space should let skilled players outplay (retreat, reposition), not just tank damage.
- Reward exploration off the critical path (loot, lore, shortcuts) — the risk/reward loop. Loop back paths (shortcuts unlocked from the far side) reduce backtracking tedium.
## Difficulty Pacing
- Introduce mechanics in a safe sandbox before lethal use; escalate by adding variables (more enemies, worse terrain, less resource), not just bigger numbers.
- Interest curve: hook early, rising complexity with rest beats, climactic peak near the end. Front-load a hook; don't save all the good stuff for later.
- Rest/save/resupply points before hard encounters set expectation and reduce frustration; checkpoints tuned to challenge length.
## Flow & Navigation
- Readable geometry: the correct path should be legible at a glance; dead-ends visually distinct from through-routes so exploration isn't punished with backtracking.
- One-way drops and locked-from-one-side doors create shortcuts and control sequence without invisible walls. Avoid invisible walls — block with believable geometry.
- Layer critical path + optional branches: mainline is obvious, secrets require a second look (peek behind, look up). Reward curiosity, never require it for the mainline.
- Sightline management: reveal the next objective/landmark as the current one completes to keep pull-forward momentum; hide reveals behind corners for surprise.
## Multiplayer / Competitive Layout
- Symmetry (mirrored maps) for fair competitive play; asymmetry with balance for objective/attack-defend modes.
- Three-lane and connector patterns control flow and flanking; chokepoints create fights, flank routes prevent stalemates.
- Cover rhythm and sightline length tune the pace: long sightlines favor snipers, short favor rushers. Spawn placement must avoid spawn-camping and spawn-kills.
## Metrics & Measurement
- Instrument playtests: heatmaps (where players go, die, get stuck), completion time, death locations, path traces, resource economy over time.
- Watch for: players missing the intended path, getting stuck at a gate, dying repeatedly at one spot (spike), or skipping content. Data over opinion for flow issues.
- Track "time to understand" a new mechanic; if players flail, the teaching beat failed.
## Iteration & Playtesting
- Playtest early and often, fresh eyes each time (a player only sees a level blind once). Watch silently — don't coach; note where they hesitate.
- Iterate blockout -> playtest -> adjust before art. Kill your darlings: cut sections that don't serve pacing.
- Note confusion points, not just deaths; hesitation = unclear guidance. Log first-time-player reactions specifically.
## Gotchas -> Fix
- **Players get lost / don't know where to go**: weak guidance. Fix: add light, leading lines, a landmark, or a visible objective marker; test with fresh eyes.
- **Level feels monotonous / exhausting**: flat pacing (all combat or all calm). Fix: build tension-release rhythm, insert rest beats and vistas between peaks.
- **Players miss the intended path/secret**: no draw or bad composition. Fix: frame it with light/lines/color contrast; A/B in playtests via heatmap.
- **Difficulty spike frustrates**: mechanic tested before taught, or too many new variables at once. Fix: teach-then-test, add a checkpoint before it, introduce one variable at a time.
- **Combat arena feels flat/boring**: symmetric box, no cover or verticality. Fix: add sightline variety, cover, flanks, chokepoints, elevation.
- **Rebuilds are expensive because art came first**: committed to layout too early. Fix: validate everything in greybox; only art-pass locked layouts.
- **Backtracking is tedious**: linear dead-ends forcing return trips. Fix: add loop-back shortcuts unlocked from the far end.
- **Inconsistent scale / player can't judge jumps**: no metric standards. Fix: build and enforce a metrics kit (jump/step/cover/door heights) across all levels.
- **Playtest feedback is vague ("it's fine")**: coaching or leading testers. Fix: watch silently, record sessions, measure hesitation/death heatmaps, ask open questions after.
- **Objective marker does all the work**: players follow the arrow blind, world design ignored. Fix: reinforce with environmental guidance so the space reads even without markers.
- **Players hit invisible walls**: arbitrary bounds break immersion. Fix: block with believable geometry (rubble, cliffs, fences), signpost the real edge.
- **Can't tell dead-ends from paths**: uniform geometry. Fix: make through-routes visually open, cap dead-ends clearly, reward them with loot to justify the detour.
- **Competitive map stalemates or spawn-camps**: bad lane/spawn layout. Fix: add flank routes, break long sightlines, relocate spawns away from chokes, add spawn protection logic.
- **Secret is mandatory, players stuck**: critical path depends on a hidden route. Fix: keep mainline obvious, make secrets purely optional rewards.
