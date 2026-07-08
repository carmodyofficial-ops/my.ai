# Game Math & Physics

## Vectors
- Normalize before scaling by speed: `vel = dir.normalized() * speed` — un-normalized diagonals move ~1.41x faster.
- Guard normalize: zero-length vector normalizes to NaN. Check `lengthSq > 1e-8` first.
- Dot product: `dot(a,b) = |a||b|cosθ`. Facing check with unit vectors: `dot(forward, toTarget) > 0.7` ≈ within ~45°; `> 0` = in front, `< 0` = behind.
- Compare distances with `lengthSq` (`dx*dx+dy*dy`) vs `radius*radius` — skip the sqrt.
- 2D "cross" `ax*by - ay*bx`: sign tells left/right of a direction — steering and winding tests. 3D cross gives the perpendicular (surface normals, camera right = `cross(forward, up)`).
- Reflect off surface normal n (unit): `r = v - 2*dot(v,n)*n` — bounces, ricochets.

## Lerp, Damping, Easing
- `lerp(a,b,t) = a + (b-a)*t`, t in [0,1]. `lerp(pos, target, 0.1)` each frame is framerate-DEPENDENT.
- Framerate-independent damping: `pos = lerp(pos, target, 1 - exp(-k*dt))` (k ≈ 5–20). Same feel at 30 and 144 fps.
- Slerp for rotations/quaternions; lerping angles directly breaks across the 359°->1° wrap.
- Easing: `easeOutQuad t*(2-t)` for UI/camera arrivals; `easeInQuad t*t` for windups; easeOutBack/elastic for juicy pop-ins. Ease the 0–1 parameter, then lerp.

## Angles & Rotation Gotchas
- `atan2(dy, dx)` gives angle to target — never `atan(dy/dx)` (loses quadrant, divides by zero).
- Shortest angular difference: `wrap(b - a)` into (-π, π]: `d = ((b-a+PI) % TAU + TAU) % TAU - PI`. Rotate toward target by `clamp(d, -maxTurn*dt, maxTurn*dt)`.
- Radians vs degrees mismatches are the top rotation bug — most math APIs take radians; many sprite APIs expose degrees. Convert at the boundary once.
- Screen Y is usually DOWN: positive rotation appears clockwise; "up" is `(0,-1)` in most 2D engines.

## Collision
- AABB overlap: `a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y`.
- Circle-circle: `distSq(c1,c2) < (r1+r2)^2`.
- Circle vs AABB: clamp circle center to box (`closest = clamp(c, min, max)`), then circle-point test.
- Separate axes when resolving AABB penetration: push out along the axis of least overlap; resolving both at once causes corner snags.
- Raycast: step or use slab method vs AABBs; for gameplay, ray from last position to current catches fast movers (see tunneling below).

## Platformer Physics
- Gravity as acceleration: `vy += g*dt; y += vy*dt` (semi-implicit Euler — update velocity BEFORE position; plain explicit Euler gains energy).
- Tune by feel: pick jump height h and time-to-apex t, derive `g = 2h/t²`, `jumpVel = -g*t`. Typical: higher gravity when falling (`g*1.8`) for snappy arcs.
- **Coyote time**: allow jump ~0.1s after walking off a ledge (`if (jumpPressed && timeSinceGrounded < 0.1)`).
- **Jump buffering**: if jump pressed ~0.1s before landing, jump on landing. Both together remove "my jump ate the input" complaints.
- Variable jump height: on button release while rising, `vy *= 0.5` (or clamp to min).
- Clamp fall speed (terminal velocity) or fast falls tunnel through platforms.
- Move and collide per-axis: move X, resolve, move Y, resolve — avoids corner-catching and lets you set `grounded` only from Y resolution.

## Useful Formulas Grab-Bag
- Distance point->segment: project point onto segment (`t = clamp(dot(p-a, b-a)/lenSq(b-a), 0, 1)`), measure to `a + t*(b-a)` — bullets vs walls, click-near-line.
- Predictive aim (constant target velocity): solve intercept time from quadratic `|targetPos + targetVel*t - shooter| = projSpeed*t`; cheap fallback: aim at `targetPos + targetVel * (dist/projSpeed)` iterated twice.
- Screen shake: offset camera by `noise(t*freq) * amplitude * trauma^2`, decay trauma linearly — noise beats random jumps, squaring makes big hits feel bigger.
- Map a value between ranges: `out = outMin + (v - inMin) * (outMax - outMin) / (inMax - inMin)`; clamp when v can exceed the input range.
- Camera deadzone follow: only move camera when target exits an inner rect; lerp-with-exp-damping toward the target thereafter.

## Random Numbers in Gameplay
- `randRange(a,b) = a + rng()*(b-a)`; random int inclusive: `floor(a + rng()*(b-a+1))`.
- Random point in circle: `r = R*sqrt(rng())`, angle `= rng()*TAU` — without the sqrt, points cluster at the center.
- Gaussian-ish variation cheaply: average 3 uniform rolls — spread values (damage, particle speed) look more natural than uniform.
- Shuffle with Fisher-Yates (`for i from n-1 down: swap(i, randInt(0,i))`) — the naive sort-by-random or swap-with-anywhere shuffles are biased.

## Fixed-Point of Reference
- Speeds in units/second, accelerations in units/second², always multiplied by dt — a tuning value that only works at one framerate is a bug in waiting.
- Timers count down in seconds; angles in radians internally; convert to degrees only for display/editor.
- Spring smoothing when exp-damping feels dead: `vel += (target - pos)*stiffness*dt; vel *= damping; pos += vel*dt` — overshoot + settle reads as organic (camera, UI, follower).
- Knockback: set velocity along `normalize(hit.pos - attacker.pos) * force`, briefly lock player input (0.1–0.2s) so the knockback is felt, then restore control.

## Gotchas -> Fix
- **Tunneling**: fast object skips thin collider between frames. Fix: continuous collision detection, cap max speed, or raycast from last position to new position.
- **Diagonal speed boost**: WASD input `(1,1)` moves 1.41x. Fix: normalize input vector when `lengthSq > 1`.
- **Lerp smoothing feels different per machine**: constant-t lerp per frame. Fix: `1 - exp(-k*dt)` factor.
- **Entity spins the long way around**: naive angle lerp across the ±π wrap. Fix: shortest-angle wrap before interpolating, or slerp quaternions.
- **NaN poisons everything**: normalizing zero vector or dividing by zero dt; NaN spreads through physics silently. Fix: guard zero-length/zero-dt; assert `isFinite` on positions in debug.
- **Jitter resting on floor**: gravity pushes in, resolution pushes out each frame. Fix: snap to surface and zero `vy` when grounded; keep a small skin/tolerance.
- **Corner snag on tile seams**: AABB catches edges between adjacent tiles. Fix: per-axis movement + least-penetration resolution; round positions to avoid float seams.
- **Floating-point drift far from origin**: physics/render precision degrades past ~10^5–10^6 units (float32). Fix: keep world coords small, or use a floating origin.
- **Frame-dependent gravity**: `vy += g` without dt works only at one framerate. Fix: always scale by dt; use fixed timestep for physics.
- **Angle stored as accumulating float**: grows unbounded over hours, precision loss. Fix: wrap into [0, TAU) after each update.
