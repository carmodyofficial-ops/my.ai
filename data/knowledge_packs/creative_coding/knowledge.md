# Creative Coding Reference (p5.js / Canvas 2D / Generative Art)

## p5.js Core
- Skeleton: `function setup(){ createCanvas(800, 600); }` runs once; `function draw(){ }` loops ~60 fps. `noLoop()` for static pieces (call `redraw()` on demand); `frameRate(30)` to throttle.
- `background(...)` at top of `draw()` clears; OMIT it to accumulate trails. Semi-transparent bg = fade trails: `background(0, 20)`.
- Coordinates: origin top-left, y down. `width`/`height`/`frameCount`/`mouseX`/`mouseY` are globals.
- Style state: `fill(r,g,b,a)`, `stroke()`, `noFill()`, `noStroke()`, `strokeWeight(2)`. Color modes: `colorMode(HSB, 360, 100, 100, 1)` — HSB is far easier for generative palettes.
- Transforms: wrap in `push()`/`pop()`; order `translate() -> rotate() -> scale()` then draw at (0,0). Rotation is in radians (`angleMode(DEGREES)` to switch).
- Shapes: `circle(x,y,d)`, `rect`, `line`, `beginShape(); vertex(x,y); endShape(CLOSE)`; smooth curves via `curveVertex`.
- Useful math: `map(v, a, b, c, d)`, `lerp(a, b, t)`, `constrain`, `dist`, `random(min, max)`, `randomGaussian()`, `noise(x)`. `randomSeed(n)`/`noiseSeed(n)` for reproducible art.
- Vectors: `let v = createVector(x, y); v.add(other); v.mult(0.9); v.setMag(3); v.heading()` — basis of particle/agent systems.

## Perlin Noise (the generative workhorse)
- `noise(x)` returns smooth 0..1; sample with SMALL steps: `noise(x * 0.01)` — step size controls smoothness (0.001 = very smooth, 0.1 = jittery).
- Time-varying field: `noise(x * 0.01, y * 0.01, frameCount * 0.005)`.
- Flow field: angle per cell `let a = noise(x*s, y*s) * TWO_PI * 2;` -> particles follow `p.vel = createVector(cos(a), sin(a))` — instant organic streams.
- Offset independent channels: `noise(t)` vs `noise(t + 1000)` for uncorrelated x/y wander.

## Particle Systems
```js
class P { constructor(){ this.pos=createVector(random(width),random(height));
  this.vel=p5.Vector.random2D(); this.acc=createVector(); this.life=255; }
  update(){ this.vel.add(this.acc); this.vel.limit(4);
    this.pos.add(this.vel); this.acc.mult(0); this.life -= 2; } }
```
- Force accumulation: `acc.add(force)` each frame, zero after integrating; velocity-limit to tame explosions.
- Kill + recycle: filter dead (`life <= 0`) or reuse via object pool — never grow the array unbounded.
- Edge behavior choices: wrap (`pos.x = (pos.x + width) % width`), bounce (negate vel component), or die.

## Easing & Motion
- Exponential ease-toward (the 90% idiom): `x += (target - x) * 0.1;` — fast then settling, no library.
- Parametric easing on t in 0..1: easeInOutQuad `t<.5 ? 2*t*t : 1-(-2*t+2)**2/2`; cubic `t*t*t`; apply then `lerp(a, b, eased)`.
- Oscillation: `sin(frameCount * 0.05) * amp`; phase-offset copies (`sin(t + i * 0.3)`) for wave ripples across many elements.
- Loop-perfect GIF trick: drive everything from `let t = (frameCount % N) / N;` and use only periodic functions of `t * TWO_PI`.

## Color for Generative Work
- Work in HSB: vary hue, lock saturation/brightness for cohesive palettes. Analogous = hue ± 30; complementary = hue + 180.
- `lerpColor(c1, c2, t)` for gradients along a path/lifetime. Sample palettes from arrays: `palette[floor(random(palette.length))]`.
- Layer with low alpha (`fill(h, s, b, 0.05)`) — thousands of translucent strokes build depth.
- Blend modes: `blendMode(ADD)` for glow/light accumulation (use dark bg), `MULTIPLY` for ink/watercolor on light bg; reset with `blendMode(BLEND)`.

## Raw Canvas 2D (no p5)
- Loop: `requestAnimationFrame(frame)`, delta-time from the timestamp arg. `ctx.clearRect(0,0,w,h)` or translucent `fillRect` for trails.
- HiDPI: `canvas.width = cssW * devicePixelRatio; ctx.scale(dpr, dpr);` CSS sets display size — else blurry.
- Path batching: one `beginPath()`, many `moveTo/lineTo`, single `stroke()` — MUCH faster than stroke-per-segment.
- `ctx.globalAlpha`, `ctx.globalCompositeOperation = 'lighter'` (additive glow), `'multiply'`.

## WebGL / Shader Basics
- p5: `createCanvas(w, h, WEBGL)` — origin moves to CENTER; 3D prims (`box`, `sphere`, `torus`), `orbitControl()` for camera.
- Custom shaders: `loadShader(vertPath, fragPath)` in `preload`, `shader(s)`, pass data via `s.setUniform('u_time', millis()/1000)`, draw a full-canvas `rect`.
- Fragment shader mental model: runs per-pixel; `gl_FragColor = vec4(r,g,b,1.0)`; normalized coords via a resolution uniform. Cheap full-screen effects (plasma, metaballs, reaction-diffusion) impossible at 60 fps on CPU.
- GLSL gotchas: floats need decimals (`1.0` not `1`); no implicit int->float; `precision mediump float;` required in p5 frag shaders.

## Performance
- Zero per-frame allocation in hot loops: reuse vectors (`v.set(x,y)`), pool particles, hoist objects out of `draw()`.
- Offscreen buffers: `let g = createGraphics(w, h);` draw static/accumulating layers once, then `image(g, 0, 0)` per frame. Raw canvas: `OffscreenCanvas` or a second hidden canvas.
- Batch state: group draws by fill/stroke; every style change flushes. `noStroke()` when unneeded (stroke is expensive on many small shapes).
- `pixels[]` access: `loadPixels()`/`updatePixels()` once per frame, not `get()`/`set()` per pixel (each is a GPU readback).
- Cap entities; degrade gracefully (fewer particles when `frameRate() < 40`).
- Big stills: render at 2-4x with a scale factor constant, `saveCanvas()`; keep all sizes relative to `width` so it scales.

## Recipes That Always Land
- Boids: three steering forces (separation, alignment, cohesion) averaged over neighbors within a radius; weight separation highest; spatial-grid the neighbor lookup past ~300 agents.
- Recursive subdivision: split a rect into 2-4 children with `random()` bias, recurse to depth n or until min size — instant Mondrian/circuit textures.
- Random walkers with `noise`-steered heading + low-alpha stroke = organic scribble fields.
- Export: `save('art.png')` / `saveCanvas()`; for print embed the seed in the filename so any output is regenerable.

## Gotchas -> Fix
- **Blurry canvas**: CSS-sized only -> set width/height attrs x devicePixelRatio, scale ctx.
- **Trails don't fade / fade to gray**: translucent background never fully clears low-alpha residue -> periodically hard-clear, or draw fade rect with `blendMode(BLEND)` and slightly higher alpha.
- **noise() looks like static**: input step too big -> multiply coords by 0.001-0.02.
- **Same "random" art every run wanted but differs**: seed it — `randomSeed(s); noiseSeed(s)` and display `s`.
- **Rotation orbits wrong point**: rotate happens about origin -> `translate(cx, cy)` first, draw at (0,0), wrap in `push()/pop()`.
- **Everything accelerates forever**: forces accumulate -> zero `acc` each frame, `vel.limit()`.
- **Frame drops with many particles**: per-frame `new`/array churn -> pooling; single batched path; offscreen static layer.
- **WEBGL sketch draws off-screen**: origin is center in WEBGL mode -> translate by `-width/2, -height/2` or design around center.
- **Shader renders black**: missing `precision mediump float;`, int/float mix (`1` vs `1.0`), or uniform name mismatch.
- **`preload` assets undefined**: loaded async -> put `loadImage`/`loadShader` in `preload()`, or use callbacks/`async` setup.
- **GIF/video loop pops**: motion driven by unbounded time -> drive from `t = (frameCount % N)/N` with periodic functions only.
- **Colors clash**: RGB random -> HSB with constrained saturation/brightness, vary hue only.
