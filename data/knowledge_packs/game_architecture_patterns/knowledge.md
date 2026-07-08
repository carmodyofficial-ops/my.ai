# Game Architecture Patterns

## Game Loop (fixed timestep + interpolation)
- Fixed update for simulation, variable render. Accumulator pattern:
```js
acc += frameDt;
while (acc >= STEP) { update(STEP); acc -= STEP; }
render(acc / STEP); // alpha for interpolation
```
- Pick `STEP` = 1/60 (or 1/50 for physics-heavy). Render interpolates between previous and current state: `pos = lerp(prevPos, currPos, alpha)` — store prev state each tick.
- Clamp `frameDt` (e.g. max 0.25s) before accumulating, else a long GC pause / tab-switch triggers the spiral of death (updates take longer than the time they simulate).
- Never put gameplay logic in render; never read wall-clock inside `update` — pass `STEP` in.

## Update/Render Separation
- Simulation owns state; render reads it. One direction of data flow: input -> update -> render.
- Keep render-only data (sprites, particles, tweens for pure visuals) out of the sim so replays/headless servers work.
- Camera shake, hit flashes, interpolation live on the render side; hitboxes, timers, cooldowns live in fixed update.

## ECS vs Inheritance
- Inheritance breaks at the diamond: `FlyingEnemy`, `SwimmingEnemy`, need `FlyingSwimmingEnemy`? Composition wins.
- Component-based (Unity-style): entity = bag of components with behavior. Simple, good default for small/medium games.
- Pure ECS (data-only components + systems iterating archetypes) pays off at thousands of entities or when you need cache-friendly iteration/serialization; overkill for a jam game.
- Practical middle ground: plain objects + mixin/behavior components + a few systems (physics, AI) that iterate tagged lists.

## State Machines
- Three distinct FSM layers — don't merge them: **game states** (menu/playing/paused), **screen/scene states**, **character states** (idle/run/jump/attack).
- Each state gets `enter()`, `update(dt)`, `exit()`. Transitions only in one place; log them while debugging.
- Character FSM: guard transitions (`canJump = grounded || coyote`), and prefer explicit states over boolean soup (`isJumping && !isFalling && wasHit` rots fast).
- Push-down automaton (state stack) for pause/inventory over gameplay: `push(PauseState)`, `pop()` resumes without re-entering.

## Object Pooling
- Pool anything spawned >~10/sec: bullets, particles, damage numbers, audio instances. Alloc+GC spikes cause frame hitches, especially in JS.
- Pattern: preallocate N, `acquire()` returns inactive instance (grow or fail loudly when empty), `release()` resets state and deactivates.
- The #1 pooling bug is stale state: write an explicit `reset()` that clears velocity, timers, event listeners, tween handles — don't trust the constructor ran.

## Event Bus
- Decouple systems: `bus.emit('enemy:died', {id, pos})`; achievements, audio, UI subscribe. Emitter shouldn't know listeners.
- Use for cross-cutting notifications, NOT for per-frame data flow (input, movement) — that becomes untraceable spaghetti.
- Always pair `on` with `off` on teardown; leaked listeners on destroyed entities are a classic crash/leak.
- Consider queued dispatch (process events at a fixed point in the frame) to avoid mid-update mutation ordering bugs.

## Scene Management
- Scene = self-contained unit: load assets, build entities, run, teardown. Explicit lifecycle: `preload/create/update/shutdown`.
- Keep persistent state (score, save data, settings) OUTSIDE scenes in a registry/service — scenes are disposable.
- Additive scenes for HUD/UI over gameplay; transition scenes (fade, loading) as their own lightweight state.
- On teardown: unsubscribe events, kill tweens/timers, release pooled objects. Most "works first time, breaks on restart" bugs are dirty teardown.

## Save Systems
- Save data, not objects: plain serializable struct (JSON) with a `version` field from day one.
- Migration ladder: `if (v < 2) migrateV1toV2(data)` chains — never break old saves.
- Save at checkpoints/explicit points, not continuously; write to temp file/key then swap, so a crash mid-write doesn't corrupt the only save.
- Don't serialize derived state (current animation frame, cached paths) — recompute on load. Do serialize RNG seed if determinism matters.

## Input Handling
- Separate raw input from actions: input layer maps device events to named actions (`"jump"`, `"dash"`), gameplay reads actions. Rebinding, replays, and AI-driving-the-player all fall out free.
- Sample input once per frame into a struct; fixed updates consume it. Reading device state inside fixed update ticks misses or double-counts presses when tick count per frame varies.
- Distinguish `pressed` (this frame), `held`, `released` — most input bugs are using `held` where `pressed` was meant.

## Time Handling
- One authoritative game clock; derive everything (`scaledDt = rawDt * timeScale`). Slow-mo, pause, and fast-forward become one variable.
- Separate clocks for UI vs gameplay: pause menus need animations while gameplay dt is 0.
- Cooldowns/timers as countdown floats decremented by dt beat timestamp comparisons — they respect time scale and pause automatically.

## Entity Lifecycle
- Never destroy entities mid-iteration of the update list — mark dead, sweep at frame end. Mid-loop removal skips or double-updates neighbors.
- Spawn queue likewise: entities created during update join NEXT frame (or at a defined flush point), so a frame has a stable entity set.
- Give entities stable ids; store references between entities as ids, not object pointers — survives serialization and dead-entity access becomes a checkable lookup instead of a stale-pointer bug.

## Debug Infrastructure (pays for itself)
- Toggleable overlays from week one: FPS + frame-time graph, entity count, collision shapes, state machine current-state labels.
- A debug console or hotkeys for: spawn X, teleport, invincibility, time scale up/down, skip-to-level. Testing a late-game bug without these costs minutes per repro.
- Deterministic replay (record inputs + seed) is the single best debugging investment if your sim is deterministic.

## Gotchas -> Fix
- **Spiral of death**: fixed updates take longer than real time, accumulator grows forever. Fix: clamp accumulated dt (max ~5 steps/frame), drop the rest.
- **Physics jitter at high refresh (144Hz)**: sim at 60Hz, render at 144Hz shows stutter. Fix: render-state interpolation with the accumulator alpha.
- **Everything-extends-Entity god class**: base class accretes health, inventory, AI. Fix: components; base entity is just id + transform.
- **Pooled bullet keeps old velocity/target**: fires sideways or homes on dead enemy. Fix: full `reset()` on acquire; assert clean state in debug builds.
- **Pause doesn't pause tweens/timers/audio**: they run on wall time. Fix: single time scale multiplier every system reads; `dt *= timeScale`.
- **Restarting a scene doubles event handlers**: enemies die twice, sounds double. Fix: unsubscribe in `shutdown`; use scene-scoped emitters that auto-clear.
- **Save file corrupt after crash during write**: partial JSON. Fix: write-to-temp + atomic rename; keep last-good backup slot.
- **State machine stuck**: transition guard fails and no fallback. Fix: log every transition attempt; add a watchdog default transition per state.
- **Frame-order coupling**: system A reads what B wrote this frame, breaks when order changes. Fix: explicit update order list, or double-buffer shared state.
- **Singleton-everywhere**: managers reach into each other, untestable. Fix: pass dependencies in constructors or a single service locator built at boot.
