# Web Game Dev Reference (HTML5 Canvas/JS)

## Game Loop
- Use `requestAnimationFrame`, NEVER `setInterval`/`setTimeout` (no vsync, drift, background throttling).
- Frame-rate independence: scale movement by delta time. `x += vx * dt`.
```js
let last = performance.now();
function frame(t){ const dt = (t - last) / 1000; last = t;
  update(dt); render(); requestAnimationFrame(frame); }
requestAnimationFrame(frame);
```
- Deterministic physics: **fixed-timestep accumulator**. Decouples sim from render.
```js
const STEP = 1/60; let acc = 0;
acc += Math.min(dt, 0.25);          // clamp dt: avoids spiral of death after tab-away
while (acc >= STEP){ update(STEP); acc -= STEP; }
render(acc / STEP);                 // alpha for interpolation between states
```
- Keep `update(dt)` (logic) strictly separate from `render()` (draw only, no state changes).
- Tab-switch: rAF pauses in background; on return dt is huge -> the clamp above. Pause music/sim on `document.visibilitychange`.

## Canvas 2D Rendering
- `const ctx = canvas.getContext('2d')`; `ctx.clearRect(0, 0, w, h)` every frame (or draw opaque bg).
- Transforms: wrap in `ctx.save()`/`ctx.restore()`; order `translate -> rotate -> scale`, then draw at origin.
- Sprites: `drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh)` — 9-arg form crops from an atlas.
- Resolution: set `canvas.width/height` ATTRIBUTES, not CSS. CSS alone stretches the bitmap -> blur.
- HiDPI: `const r = devicePixelRatio; canvas.width = cssW*r; canvas.height = cssH*r; ctx.scale(r,r);` with CSS width/height at cssW/cssH.
- Pixel art: `ctx.imageSmoothingEnabled = false` + CSS `image-rendering: pixelated`; keep positions integer (`x|0`) to avoid shimmer.
- Camera: `ctx.translate(-camX, -camY)` inside save/restore; cull entities outside viewport before drawing.

## Sprites & Atlases
- Pack frames into one sheet/atlas: one image = fewer requests, enables draw batching, atlas JSON maps `name -> {x,y,w,h}`.
- Sprite-sheet animation: `sx = frame * fw`; advance via accumulated time, not per-frame ++: `animT += dt; frame = Math.floor(animT / frameDur) % frameCount;`.
- Preload before loop; never draw an unloaded image.
```js
const load = src => new Promise((res, rej) => { const i = new Image();
  i.onload = () => res(i); i.onerror = rej; i.src = src; });
const imgs = await Promise.all(srcs.map(load));
```
- Show a loading bar: count resolved promises; games feel broken without one.

## Input
- Track held keys in a Set; act in `update`, not the event (events fire at OS repeat rate, not frame rate).
```js
const keys = new Set();
onkeydown = e => { keys.add(e.code); if (e.code === 'Space') e.preventDefault(); };
onkeyup   = e => keys.delete(e.code);
// in update: if (keys.has('ArrowLeft')) x -= spd * dt;
```
- Use `e.code` (physical key, layout-independent), not `e.key`. Edge-trigger (jump) = "pressed this frame" set cleared each update.
- Mouse -> canvas coords: `const r = canvas.getBoundingClientRect(); mx = (e.clientX - r.left) * (canvas.width / r.width);` — rescale when canvas CSS size differs from attribute size.
- Gamepad: poll `navigator.getGamepads()` each frame after a `gamepadconnected` event; no push events for sticks/buttons.

## Mobile Touch
- Use Pointer Events (`pointerdown/move/up`) to unify mouse+touch; or touch events with `e.preventDefault()` to stop scroll/zoom.
- CSS on canvas: `touch-action: none;` (kills browser gestures), `user-select: none;`.
- Multi-touch: track by `e.pointerId` / `changedTouches[i].identifier` in a Map — supports left-thumb stick + right-thumb button simultaneously.
- Virtual controls: draw joystick/buttons on canvas, hit-test touches; size targets >= 48 px; keep in thumb-reach corners.
- `window.addEventListener('resize', ...)` + orientation: recompute canvas size and DPR scaling; letterbox to preserve aspect.

## Collision
- AABB: `a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y`.
- Circle: `dx*dx + dy*dy < (ar+br)**2` (no `sqrt`).
- Resolution: compute minimal overlap axis, push out along it; resolve X and Y separately for platformers (move X, test, then Y, test) to get clean wall/floor behavior.
- Fast movers tunnel through thin walls -> substep movement or ray/swept-AABB test.
- Many objects: **spatial hash grid** (cell ~= max entity size); test only same+neighbor cells. Kills O(n^2).

## Audio (Web Audio API)
- Web Audio for SFX (low latency, overlap, pitch); `<audio>` acceptable for one music stream.
- Autoplay policy: context starts suspended -> `ac.resume()` inside the first user gesture (click/keydown/touch).
```js
const ac = new AudioContext();
const buf = await ac.decodeAudioData(await (await fetch('hit.wav')).arrayBuffer());
function sfx(buf, vol=1){ const s = ac.createBufferSource(); s.buffer = buf;
  const g = ac.createGain(); g.gain.value = vol;
  s.connect(g).connect(ac.destination); s.start(); }
```
- `BufferSource` is one-shot — create a new one per play (cheap); the decoded buffer is reused.
- Master volume/mute: single `GainNode` before destination. Pitch variation: `s.playbackRate.value = 0.9 + Math.random()*0.2` de-robotizes repeated SFX.

## Entities & State
- Scene state machine: `state = 'menu'|'play'|'pause'|'over'`; switch in update/render; or object-per-scene with `enter/exit/update/render`.
- `entities` array; update all, then render all. Mark `dead`, sweep after the loop (never splice while iterating).
- **Object pooling** for bullets/particles: preallocate, toggle `active`, no `new` in hot path -> avoids GC stutter.

## Performance & Profiling
- DevTools Performance tab: record 5-10 s, look for long frames (> 16.7 ms); flame chart shows whether update, render, or GC is the cost. Sawtooth memory in the Memory graph = allocation churn -> pool.
- On-screen meter: rolling average of dt; also `performance.now()` around update vs render to attribute budget.
- Zero per-frame allocation in hot paths (no array literals, closures, string concat, `.map/.filter` in the loop).
- Layered canvases: static background on its own canvas drawn once; only redraw dynamic layer. Pre-render complex vector art / text / gradients to offscreen canvas, then `drawImage` it (text fills are slow).
- Batch by texture/style: minimize `fillStyle`/transform changes; group same-atlas draws.
- `ctx.shadowBlur` and large `filter`s are extremely slow — pre-render glows into sprites.

## Engines (when to leave raw canvas)
- **PixiJS**: fast WebGL 2D renderer, thousands of sprites; you supply game logic.
- **Phaser**: full 2D framework (physics, input, tilemaps, scenes, loader) — fastest to ship.
- Raw canvas: small/custom games, learning, minimal footprint, full control.

## Gotchas -> Fix
- `setInterval` loop -> `requestAnimationFrame`.
- Movement w/o dt (speed varies by FPS) -> multiply by dt / fixed timestep.
- Blurry canvas -> width/height attrs x devicePixelRatio, not CSS sizing.
- Acting inside keydown (OS repeat rate, missed combos) -> store key state, read in update.
- Huge dt after tab-away teleports player -> clamp dt (`Math.min(dt, 0.25)`); pause on `visibilitychange`.
- GC stutter -> pool objects, hoist allocations out of the loop.
- Silent audio -> `AudioContext.resume()` in first user gesture.
- Page scrolls/zooms on mobile drag -> `touch-action: none` + `preventDefault` on pointer/touch handlers.
- Mouse coords wrong on scaled canvas -> rescale by `canvas.width / rect.width`.
- Bullet passes through wall -> substep or swept-AABB for fast movers.
- Sprite shimmer/seams in pixel art -> integer positions, `imageSmoothingEnabled = false`, 1 px padding between atlas frames.
- Splicing entity array mid-iteration skips items -> mark dead, sweep after.
- "Spiral of death" (updates can't catch up) -> clamp accumulator input.
