# Web Game Dev Reference (HTML5 Canvas/JS)

## Game Loop
- Use `requestAnimationFrame`, NEVER `setInterval`/`setTimeout` (no vsync, drift, background throttling).
- Frame-rate independence: scale movement by delta time. `x += vx * dt`.
```js
let last=performance.now();
function frame(t){ const dt=(t-last)/1000; last=t;
  update(dt); render(); requestAnimationFrame(frame); }
requestAnimationFrame(frame);
```
- Deterministic physics: **fixed-timestep accumulator**. Decouples sim from render.
```js
const STEP=1/60; let acc=0;
acc+=Math.min(dt,0.25);           // clamp to avoid spiral of death
while(acc>=STEP){ update(STEP); acc-=STEP; }
render(acc/STEP);                  // alpha for interpolation
```
- Keep `update(dt)` (logic) separate from `render()` (draw only).

## Canvas 2D
- `const ctx=canvas.getContext('2d')`; `ctx.clearRect(0,0,w,h)` every frame.
- Transforms: wrap in `ctx.save()`/`ctx.restore()`; `translate->rotate->scale` then draw at origin.
- Sprites: `drawImage(img,sx,sy,sw,sh,dx,dy,dw,dh)`. Shapes: `fillRect`, `arc`, `beginPath`/`lineTo`/`fill`.
- Resolution: set `canvas.width/height` ATTRIBUTES, not CSS. CSS only stretches the bitmap -> blur.
- HiDPI: `const r=devicePixelRatio; canvas.width=cssW*r; canvas.height=cssH*r; ctx.scale(r,r);` style sets cssW/cssH.

## Assets
- Preload before loop; never draw an unloaded image.
```js
const load=src=>new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.src=src});
const imgs=await Promise.all(srcs.map(load));
```
- Sprite-sheet animation: pick frame via source-rect `sx=frame*fw`.

## Input
- Track held keys in a Set; act in `update`, not the event.
```js
const keys=new Set();
onkeydown=e=>{keys.add(e.code); if(e.code==='Space')e.preventDefault();};
onkeyup=e=>keys.delete(e.code);
// update: if(keys.has('ArrowLeft')) x-=spd*dt;
```
- Mouse: `const r=canvas.getBoundingClientRect(); mx=e.clientX-r.left`. Use pointer/touch events for mobile; `preventDefault` on touch to stop scroll.

## Collision
- AABB: `a.x<b.x+b.w && a.x+a.w>b.x && a.y<b.y+b.h && a.y+a.h>b.y`.
- Circle: `dx*dx+dy*dy < (ar+br)**2` (avoid `sqrt`).
- Many objects: bucket into a **spatial grid** (cell=max entity size); only test same/neighbor cells. Avoids O(n^2).

## State & Entities
- State machine: `state='menu'|'play'|'pause'|'over'`; switch in update/render.
- `entities` array; loop update then render. Mark `dead`, sweep after.
- **Object pooling**: reuse bullet/particle objects (set `active=false`) instead of `new` -> avoids GC stutter.

## Audio
- Web Audio API for low-latency SFX, not `<audio>`.
- Autoplay policy: `ctx.resume()` inside first user gesture (click/keydown).
```js
const ac=new AudioContext();
function sfx(buf){const s=ac.createBufferSource();s.buffer=buf;s.connect(ac.destination);s.start();}
```

## Performance
- Zero per-frame allocation in hot paths (no array/object/closure churn).
- Layered/offscreen canvases: static bg drawn once; redraw only changed layers.
- Batch same-texture draws; minimize state changes (`fillStyle`, transforms).
- Cap effects by dt; pre-render complex shapes to an offscreen canvas.

## Engines (when to leave raw canvas)
- **PixiJS**: fast WebGL 2D renderer, thousands of sprites; you supply game logic.
- **Phaser**: full 2D framework (physics, input, tilemaps, scenes) — fastest to ship.
- Raw canvas: small/custom games, learning, minimal footprint.

## Gotchas -> Fix
- `setInterval` loop -> `requestAnimationFrame`.
- Movement w/o dt (varies by FPS) -> multiply by dt / fixed step.
- Blurry canvas -> set width/height attrs + devicePixelRatio, not CSS size.
- Acting in keydown (misses combos/repeat) -> store state, read in update.
- GC stutter -> pool objects, hoist allocations.
- Silent audio -> `AudioContext.resume()` after user gesture.
- "Spiral of death" -> clamp `dt` before accumulator.
