---
name: web-frontend
description: "How to build browser frontends and HTML5 canvas games: the requestAnimationFrame + delta-time game loop, update/render split, input caching, AABB collision, DOM events, and avoiding the usual frame-rate / XSS / layout-thrash mistakes."
version: 1.0.0
category: Coding
tags: [web, frontend, html, css, javascript, canvas, game, web game, dom, requestanimationframe, browser, ui, fetch, sprite, collision]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when building a browser UI or a web (HTML5 canvas) game — game loops, rendering, input, DOM/CSS, or fetch-driven frontends.

## Procedure

1. Structure a web game as three files (or sections): `index.html` (a `<canvas>` + script tag), `style.css`, `game.js`. Keep state in plain objects.
2. Drive the game with ONE loop using `requestAnimationFrame` and **delta time** (seconds since last frame), so motion is frame-rate independent. Split it: `update(dt)` mutates state, `render()` draws. Clear the canvas (`ctx.clearRect`) at the start of every render.
3. Handle input by caching: `keydown`/`keyup` set flags on a `keys` object; the loop reads those flags. Never move or run game logic inside the event handler itself.
4. Collisions: axis-aligned bounding boxes — `a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y`. Model entities as `{x,y,w,h,vx,vy}`.
5. Use a small state machine (`menu`/`play`/`gameover`) and branch update/render on it. Load images before starting the loop (`img.onload`).
6. For general frontend: use `addEventListener` (delegate via `e.target.closest()` for lists), build DOM with `textContent` (never `innerHTML` for user data — XSS), and do `fetch` with `await` + a timeout + an `if (!r.ok) throw`. Lay out with flexbox/grid, not floats/absolute hacks.
7. Verify by opening the page (or a quick `python3 -m http.server`) and checking the browser console for errors; confirm motion is smooth and input responsive.

## Pitfalls

- Movement multiplied by frames not `dt` → speed varies with hardware. Always `pos += vel * dt`.
- Forgetting `clearRect` each frame → smear trails. Clamp `dt` (e.g. `min(dt, 0.05)`) so a tab-stall doesn't teleport everything.
- Reading input inside the loop instead of caching from events; running game logic in handlers.
- `innerHTML = userInput` → XSS; use `textContent` / `createElement`.
- Listeners never removed on teardown → leaks; use `AbortController` or `removeEventListener`.
- Layout thrash: interleaving DOM reads (`offsetWidth`) and writes forces reflow — batch reads, then writes.
- Blocking the main thread with heavy loops → jank; chunk work or use a Web Worker.

## Verification

- The game loop uses rAF + `dt`; `update`/`render` are separate; the canvas is cleared each frame.
- Input is event-cached; collisions use AABB; there is a clear state machine.
- No `innerHTML` with untrusted data; fetch has error handling; the browser console is clean.
