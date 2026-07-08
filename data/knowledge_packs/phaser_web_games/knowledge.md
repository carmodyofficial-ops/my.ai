# Phaser 3 Web Games

## Scenes & Lifecycle
- Scene methods run in order: `init(data)` -> `preload()` -> `create(data)` -> `update(time, delta)` per frame. `delta` is in **milliseconds**.
- Start scenes: `this.scene.start('Game', {level: 2})` (stops current), `this.scene.launch('HUD')` (runs in parallel), `this.scene.pause/resume/stop`.
- Pass data via the second arg of `start`; read it in `init(data)`/`create(data)`. Share persistent state via `this.registry.set/get` — survives scene restarts.
- Scene keys come from `super('Game')` or config `{ key: 'Game' }`; duplicate keys fail silently-ish.

## Game Config Essentials
```js
new Phaser.Game({
  type: Phaser.AUTO, width: 960, height: 540,
  physics: { default: 'arcade', arcade: { gravity: { y: 900 }, debug: true } },
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [BootScene, GameScene, UIScene],
  pixelArt: true // nearest-neighbor, no texture smoothing
});
```

## Loading & Sprites
- All loads in `preload()`: `this.load.image('sky','sky.png')`, `this.load.spritesheet('dude','dude.png',{frameWidth:32,frameHeight:48})`, `this.load.atlas`, `this.load.tilemapTiledJSON`.
- Loading outside preload needs manual `this.load.start()` + `once('complete', ...)`.
- Animations are GLOBAL: create once (e.g. boot scene) with `this.anims.create({key:'run', frames:this.anims.generateFrameNumbers('dude',{start:0,end:3}), frameRate:10, repeat:-1})`; recreating same key errors/warns.
- Play: `sprite.play('run', true)` — second arg `ignoreIfPlaying` avoids restarting every frame in update.

## Arcade Physics
- `this.physics.add.sprite(x,y,'dude')` gives `body`. `setVelocityX(160)`, `setBounce(0.2)`, `setCollideWorldBounds(true)`.
- `this.physics.add.collider(player, platforms)` separates bodies; `overlap(player, coins, cb)` only fires callback.
- Static groups for platforms: `this.physics.add.staticGroup()`; after moving/scaling a static body call `refreshBody()`.
- Grounded check: `player.body.blocked.down` (vs tiles/world) or `touching.down` (vs bodies).
- Body ≠ sprite: `setSize(w,h)` / `setOffset(x,y)` to fit hitbox to art; debug draw via physics config `debug: true`.

## Input
- Keyboard: `this.cursors = this.input.keyboard.createCursorKeys()`; custom `this.input.keyboard.addKeys('W,A,S,D')`. One-shot press: `Phaser.Input.Keyboard.JustDown(key)` in update.
- Pointer: `this.input.on('pointerdown', p => ...)`; per-object: `sprite.setInteractive().on('pointerdown', ...)`.
- Objects need `setInteractive()` before receiving pointer events; pass a shape for non-rect hit areas.

## Tilemaps (Tiled)
- `const map = this.make.tilemap({key:'map'}); const tiles = map.addTilesetImage('tilesetNameInTiled','tilesKey'); const layer = map.createLayer('Ground', tiles);`
- First arg of `addTilesetImage` must EXACTLY match the tileset name inside Tiled, not the file name.
- Collision: `layer.setCollisionByProperty({collides:true})` (set the bool property on tiles in Tiled) or `setCollisionByExclusion([-1])`; then `this.physics.add.collider(player, layer)`.
- Export Tiled maps as JSON; embed tilesets in the map (external .tsx needs extra handling).

## Camera & Scale
- `this.cameras.main.startFollow(player, true, 0.1, 0.1)` (lerp args smooth follow); `setBounds(0,0,map.widthInPixels,map.heightInPixels)` stops showing void.
- UI that shouldn't scroll: `setScrollFactor(0)`, or better, a parallel UI scene with its own camera.
- Effects: `this.cameras.main.shake(100, 0.01)`, `.flash()`, `.fadeOut(250)` + `once('camerafadeoutcomplete', ...)` for transitions.
- `Scale.FIT` letterboxes preserving aspect; `RESIZE` changes game size (you must handle relayout via `this.scale.on('resize')`).

## Groups, Pooling, Spawning
- `this.physics.add.group({ classType: Bullet, maxSize: 30, runChildUpdate: true })` — built-in pool: `group.get(x, y)` returns an inactive member or null at maxSize.
- On acquire: `setActive(true).setVisible(true)` and reset the body (`body.enable = true`, velocity). On release: reverse all of it — `killAndHide()` alone leaves the body colliding.
- `runChildUpdate: true` calls each child's `preUpdate/update`; forget it and pooled sprites' own logic silently never runs.

## Timers & Tweens
- Delayed call: `this.time.delayedCall(500, cb, [], this)`; repeating: `this.time.addEvent({delay: 1000, loop: true, callback: cb})`. These are scene-scoped — auto-cleaned on scene shutdown, unlike `setTimeout` (never use `setTimeout` for gameplay).
- Tweens: `this.tweens.add({targets: sprite, alpha: 0, duration: 300, ease: 'Power2', onComplete: ...})`. Yoyo + repeat for pulses; `this.tweens.killTweensOf(sprite)` before destroying targets.

## Audio
- Browsers block audio until a user gesture: start looped music on first `pointerdown`, or Phaser unlocks the context on first input automatically — but a play() call before that is dropped silently.
- `this.sound.add('sfx')` once, reuse; `this.sound.play('sfx', {volume: 0.5, rate: 1 + (Math.random()-0.5)*0.2})` — small rate variance stops repetitive-sound fatigue.

## Text & UI
- Bitmap text (`this.add.bitmapText`) is far cheaper than `this.add.text` for frequently-changing values (score counters) — canvas Text re-rasterizes on every `setText`.
- `setDepth(n)` controls draw order explicitly; relying on creation order breaks when you refactor spawning.

## Containers & Depth
- `this.add.container(x, y, [bg, icon, label])` groups objects under one transform — move/scale/tween the container, children follow. Note: Arcade physics bodies on container CHILDREN don't follow the container; put the body on the container itself.
- Depth sorting for top-down games: `sprite.setDepth(sprite.y)` each frame gives painter's-order overlap for free.

## Registry, Events, and Cross-Scene Data
- `this.registry.set('score', 0)` / `this.registry.get('score')` — global key-value store; listen with `this.registry.events.on('changedata-score', cb)` so the HUD scene updates without coupling.
- Scene-to-scene messaging: `this.scene.get('HUD').events.emit('damage', 10)` or a shared `this.game.events` emitter; always remove listeners on shutdown.

## Performance in Phaser
- Texture atlases (TexturePacker) over many single images — fewer texture swaps, faster loads.
- Cull off-screen work yourself: `setVisible(false)` isn't enough for physics bodies; also `body.enable = false` for far-away entities.
- Particles (`this.add.particles`) are cheap; hundreds of individual sprites with tweens are not — prefer emitters for effects.

## Gotchas -> Fix
- **Black screen, no errors**: asset path 404s (check network tab) or scene key mismatch in `scene.start`. Fix: verify keys and paths; add `this.load.on('loaderror', console.error)`.
- **`this` is wrong in callbacks**: classic function loses scene context. Fix: arrow functions, or pass `this` as context arg (`collider(a,b,cb,undefined,this)`).
- **Physics body doesn't match sprite art**: default body = full frame incl. transparent padding. Fix: `body.setSize/setOffset`; enable physics debug to see it.
- **Static platform moved but collisions use old spot**: static bodies cache position. Fix: `refreshBody()` after transform changes.
- **Animation restarts every frame**: `play('run')` in update. Fix: `play('run', true)` or check `anims.currentAnim.key` first.
- **JustDown always false**: created key each frame. Fix: create keys once in `create()`, store on the scene.
- **Tilemap renders but no collision**: forgot `setCollisionByProperty` / property not set in Tiled, or collider added before layer collision set. Fix: set collision first, then add collider; debug with `layer.renderDebug(gfx)`.
- **Restarting scene doubles timers/events**: listeners added to global emitters persist. Fix: use scene events or clean up in `shutdown` (`this.events.once('shutdown', ...)`).
- **Blurry pixel art**: default linear filtering + fractional positions. Fix: `pixelArt: true` in config and round camera/sprite positions.
- **delta assumed to be seconds**: movement 1000x off or tuned wrong. Fix: Phaser `update(time, delta)` delta is ms — `speed * delta / 1000`, or use physics velocities which are px/sec.
- **Gravity applied to UI/pickups flying off**: physics sprites default to dynamic. Fix: `body.setAllowGravity(false)` or use static/plain images for UI.
