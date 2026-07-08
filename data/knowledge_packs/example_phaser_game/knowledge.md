# Worked example: Phaser 3 + TypeScript arcade game (asteroid dodger, Vite)

File tree:

```
asteroid-dodger/
  index.html          # mount point + module script tag
  package.json        # phaser + vite, nothing else
  tsconfig.json
  src/
    main.ts           # Phaser.Game config — arcade physics, one scene
    GameScene.ts      # the whole game: preload/create/update
```

Architecture decisions:
- Single scene; restart = `this.scene.restart()`, which re-runs `create()` and rebuilds all state — so every mutable field is reset at the top of `create()`, never in the constructor.
- Zero external assets: textures are drawn once with `this.make.graphics(...)` and baked via `generateTexture()` in `preload()`. Loads instantly, no asset pipeline, no CORS issues.
- Arcade physics with no gravity; asteroids get a downward velocity at spawn. Collision is `physics.add.overlap` (dodger — nothing should bounce).
- Spawning via `this.time.addEvent({ loop: true })`, with the delay ramped down over time for difficulty. Off-screen asteroids are destroyed in `update()` so the group never grows unbounded.

The core file — `src/GameScene.ts`:

```ts
import Phaser from 'phaser';

const WIDTH = 800;
const HEIGHT = 600;

export default class GameScene extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Image;
  private asteroids!: Phaser.Physics.Arcade.Group;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private scoreText!: Phaser.GameObjects.Text;
  private score = 0;
  private elapsed = 0;
  private gameOver = false;
  private spawnTimer!: Phaser.Time.TimerEvent;

  constructor() {
    super('game');
  }

  preload(): void {
    // Bake textures from vector draws — no external assets.
    const g = this.make.graphics({ x: 0, y: 0 }, false);
    g.fillStyle(0x4ade80);
    g.fillTriangle(16, 0, 0, 32, 32, 32);      // ship: green triangle
    g.generateTexture('ship', 32, 32);
    g.clear();
    g.fillStyle(0x94a3b8);
    g.fillCircle(14, 14, 14);                   // asteroid: grey circle
    g.generateTexture('asteroid', 28, 28);
    g.destroy();                                // graphics object no longer needed
  }

  create(): void {
    // scene.restart() re-runs create(); reset all run state here
    this.score = 0;
    this.elapsed = 0;
    this.gameOver = false;

    this.player = this.physics.add.image(WIDTH / 2, HEIGHT - 60, 'ship');
    this.player.setCollideWorldBounds(true);
    this.player.body!.setSize(24, 24);          // forgiving hitbox

    this.asteroids = this.physics.add.group();
    this.cursors = this.input.keyboard!.createCursorKeys();

    this.scoreText = this.add.text(12, 10, 'Score: 0', {
      fontFamily: 'monospace',
      fontSize: '20px',
      color: '#e2e8f0',
    });

    this.spawnTimer = this.time.addEvent({
      delay: 650,
      loop: true,
      callback: this.spawnAsteroid,
      callbackScope: this,
    });

    this.physics.add.overlap(this.player, this.asteroids, this.onHit, undefined, this);
  }

  private spawnAsteroid(): void {
    const x = Phaser.Math.Between(20, WIDTH - 20);
    const asteroid = this.asteroids.create(x, -30, 'asteroid') as Phaser.Physics.Arcade.Image;
    asteroid.setVelocity(Phaser.Math.Between(-40, 40), Phaser.Math.Between(160, 340));
    asteroid.setAngularVelocity(Phaser.Math.Between(-120, 120));
  }

  update(_time: number, delta: number): void {
    if (this.gameOver) return;

    // survival time is the score
    this.elapsed += delta;
    this.score = Math.floor(this.elapsed / 100);
    this.scoreText.setText(`Score: ${this.score}`);

    // difficulty ramp: spawn faster as time passes (floor at 220 ms)
    this.spawnTimer.delay = Math.max(220, 650 - this.elapsed / 60);

    const speed = 320;
    this.player.setVelocity(0, 0);
    if (this.cursors.left.isDown) this.player.setVelocityX(-speed);
    else if (this.cursors.right.isDown) this.player.setVelocityX(speed);
    if (this.cursors.up.isDown) this.player.setVelocityY(-speed);
    else if (this.cursors.down.isDown) this.player.setVelocityY(speed);

    // cull asteroids that left the screen so the group stays small
    for (const child of this.asteroids.getChildren()) {
      const a = child as Phaser.Physics.Arcade.Image;
      if (a.y > HEIGHT + 40) a.destroy();
    }
  }

  private onHit(): void {
    if (this.gameOver) return;                  // overlap can fire multiple times
    this.gameOver = true;
    this.physics.pause();
    this.spawnTimer.remove();
    this.player.setTint(0xef4444);

    this.add
      .text(WIDTH / 2, HEIGHT / 2, `Game Over\nScore: ${this.score}\n\nPress SPACE to restart`, {
        fontFamily: 'monospace',
        fontSize: '28px',
        color: '#f8fafc',
        align: 'center',
      })
      .setOrigin(0.5);

    this.input.keyboard!.once('keydown-SPACE', () => this.scene.restart());
  }
}
```

---

## `src/main.ts` — game config

Arcade physics with zero gravity (a top-down dodger steers by velocity, not gravity). `Phaser.Scale.FIT` keeps the fixed 800x600 playfield crisp at any window size.

```ts
import Phaser from 'phaser';
import GameScene from './GameScene';

new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: 800,
  height: 600,
  backgroundColor: '#0f172a',
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { x: 0, y: 0 },
      debug: false,
    },
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  scene: [GameScene],
});
```

## `index.html` — project root

Vite serves this as the entry point and resolves the module script itself; no bundler config file is needed.

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Asteroid Dodger</title>
    <style>
      body { margin: 0; background: #020617; display: grid; place-items: center; min-height: 100vh; }
    </style>
  </head>
  <body>
    <div id="game"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

## `package.json`

```json
{
  "name": "asteroid-dodger",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "phaser": "^3.87.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

## `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

## How to run

```bash
mkdir asteroid-dodger && cd asteroid-dodger
npm init -y
npm install phaser
npm install -D vite typescript
# create the files above, then:
npx vite            # dev server at http://localhost:5173
npx vite build      # production bundle in dist/
```

Or scaffold with `npm create vite@latest asteroid-dodger -- --template vanilla-ts`, then `npm install phaser` and replace `index.html` and `src/` with the files above.

## Behavior summary

Arrow keys steer the ship in all four directions, clamped to the screen by `setCollideWorldBounds`. Grey asteroids rain from the top with randomized drift, fall speed, and spin; the spawn interval tightens from 650 ms toward 220 ms as the run goes on. Score is survival time in tenths of a second. Touching an asteroid pauses physics, tints the ship red, shows the final score, and Space restarts the scene from a clean state. The `gameOver` guard in `onHit` matters: arcade overlap fires every frame while bodies intersect, so without it the game-over text would stack.

Common variations that drop straight into this skeleton: give asteroids `setCircle(14)` for a round body instead of the default box; add a starfield with a second generated 2x2 white texture and a `Phaser.GameObjects.Particles` emitter; persist a high score in `localStorage` inside `onHit` and print it on the game-over card.

## Pitfalls this example already avoids (keep avoiding them)

- **State reset in the constructor instead of `create()`.** `scene.restart()` does not construct a new scene object — it re-runs `init/preload/create` on the same instance. Fields initialized only in the constructor (or as class-field defaults that you then mutate) keep their old values after restart. That is why `score`, `elapsed`, and `gameOver` are re-assigned at the top of `create()`.
- **Overlap firing every frame.** `physics.add.overlap` calls its handler on every frame the bodies intersect; the `if (this.gameOver) return;` guard in `onHit` prevents stacked game-over text and repeated tint/pause calls. The same guard pattern applies to any "touch once" mechanic (pickups should `destroy()` themselves immediately instead).
- **Leaking spawned objects.** A looped timer plus a physics group grows forever unless something culls. Here `update()` destroys anything past the bottom edge; the alternative is `this.asteroids = this.physics.add.group({ maxSize: 40 })` with `get()`-based pooling, which avoids allocation entirely at the cost of manually re-enabling recycled bodies (`setActive(true).setVisible(true)` and `body.enable = true`).
- **Moving a physics sprite by `x`/`y`.** Position writes fight the physics step. All movement here goes through `setVelocity*`; the world-bounds clamp then comes for free from `setCollideWorldBounds(true)`.
- **Using `collider` where `overlap` is meant.** A collider applies separation and bounce — the ship would shove asteroids around before dying. Dodgers, pickups, and hit detection want `overlap`.
- **Forgetting `callbackScope`** (or an arrow wrapper) on `time.addEvent`, which leaves `this` undefined inside the spawn callback in strict-mode ES modules.

## Texture generation notes

`this.make.graphics({ x: 0, y: 0 }, false)` creates a Graphics object *without* adding it to the display list (the `false`), so nothing flashes on screen before `generateTexture` bakes it into the texture manager under a string key. After baking, the Graphics object is dead weight — `destroy()` it. Keys behave exactly like loaded-image keys: `this.physics.add.image(x, y, 'ship')`, group `create(x, y, 'asteroid')`, particles, tilesprites all accept them. Draw at the size you intend to display; scaling a 32 px bake up to 128 px will look blurry, so bake at final size instead.

If you later switch to real art, only `preload()` changes: replace the graphics block with `this.load.image('ship', 'assets/ship.png')` and keep every other line of the scene identical — a good reason to route all texture access through string keys from day one.

## TypeScript strictness notes

Under `"strict": true`, Phaser's lazily-initialized members need the definite-assignment `!` on class fields (`private player!: ...`) because they are set in `create()`, not the constructor. The non-null assertions on `this.input.keyboard!` and `this.player.body!` are correct here: keyboard input exists in every desktop browser config, and an arcade image always has a body once created via `this.physics.add`. If you target touch devices, replace the keyboard block with pointer following — `const p = this.input.activePointer; this.physics.moveTo(this.player, p.worldX, p.worldY, speed);` in `update()` — and gate it on `p.isDown`.

## Difficulty ramp alternatives

The linear `spawnTimer.delay` ramp is the simplest knob, but two other levers combine well: increase the velocity range in `spawnAsteroid` as `elapsed` grows (faster rocks read as harder even at the same density), or spawn in short bursts by giving the timer a random `delay` re-roll each tick (`this.spawnTimer.reset({ delay: Phaser.Math.Between(200, 700), loop: true, callback: this.spawnAsteroid, callbackScope: this })`). Cap every ramp — an uncapped difficulty curve turns into a wall of rocks within a minute.
