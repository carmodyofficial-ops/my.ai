# Breakout — Complete single-file HTML5 Canvas Example

A minimal, runnable Breakout in one `index.html` to pattern-match: the delta-time
game loop, cached input, AABB collision, a state machine, and score.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Breakout</title>
<style>
  html,body{margin:0;height:100%;background:#111;display:grid;place-items:center}
  canvas{background:#000;border:1px solid #444;touch-action:none}
</style>
</head>
<body>
<canvas id="c" width="480" height="360"></canvas>
<script>
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const W = cv.width, H = cv.height;

// Input: handlers only cache key state, no game logic here.
const keys = {};
addEventListener('keydown', e => { keys[e.key] = true; });
addEventListener('keyup',   e => { keys[e.key] = false; });

// Entities as {x,y,w,h,vx,vy}
const paddle = { x: W/2-40, y: H-24, w: 80, h: 12, vx: 0, vy: 0 };
const ball   = { x: W/2, y: H/2, w: 10, h: 10, vx: 150, vy: -180 };
let bricks = [], score = 0, state = 'play';

function reset() {
  bricks = [];
  for (let r = 0; r < 4; r++)
    for (let col = 0; col < 8; col++)
      bricks.push({ x: 8+col*58, y: 30+r*22, w: 52, h: 16, alive: true });
  ball.x = W/2; ball.y = H/2; ball.vx = 150; ball.vy = -180;
  score = 0; state = 'play';
}

// Axis-aligned bounding box overlap test.
function hit(a, b) {
  return a.x < b.x+b.w && a.x+a.w > b.x &&
         a.y < b.y+b.h && a.y+a.h > b.y;
}

function update(dt) {
  if (state !== 'play') {
    if (keys[' ']) reset();
    return;
  }
  // Paddle: velocity from cached keys, position from velocity.
  paddle.vx = (keys['ArrowRight']?1:0) - (keys['ArrowLeft']?1:0);
  paddle.x += paddle.vx * 320 * dt;
  paddle.x = Math.max(0, Math.min(W-paddle.w, paddle.x));

  // Ball: pos += vel * dt
  ball.x += ball.vx * dt;
  ball.y += ball.vy * dt;

  if (ball.x <= 0 || ball.x+ball.w >= W) ball.vx *= -1;
  if (ball.y <= 0) ball.vy *= -1;
  if (ball.y > H) { state = 'gameover'; }

  if (hit(ball, paddle) && ball.vy > 0) ball.vy *= -1;

  for (const b of bricks) {
    if (b.alive && hit(ball, b)) {
      b.alive = false; ball.vy *= -1; score += 10;
    }
  }
  if (bricks.every(b => !b.alive)) state = 'gameover';
}

function render() {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0cf';
  ctx.fillRect(paddle.x, paddle.y, paddle.w, paddle.h);
  ctx.fillStyle = '#fff';
  ctx.fillRect(ball.x, ball.y, ball.w, ball.h);
  for (const b of bricks)
    if (b.alive) { ctx.fillStyle = '#e64'; ctx.fillRect(b.x, b.y, b.w, b.h); }
  ctx.fillStyle = '#fff';
  ctx.font = '14px monospace';
  ctx.fillText('Score: ' + score, 8, 18);
  if (state === 'gameover') {
    ctx.textAlign = 'center';
    ctx.fillText('GAME OVER - press SPACE', W/2, H/2);
    ctx.textAlign = 'left';
  }
}

let last = performance.now();
function loop(now) {
  const dt = Math.min((now - last) / 1000, 0.05); // seconds, clamped
  last = now;
  update(dt);
  render();
  requestAnimationFrame(loop);
}
reset();
requestAnimationFrame(loop);
</script>
</body>
</html>
```
