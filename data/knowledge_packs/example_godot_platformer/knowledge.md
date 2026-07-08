# Worked example: Godot 4.x 2D platformer (GDScript, static typing)

Scene/file tree:

```
res://
  project.godot            # input map + autoload registered here
  scripts/game_state.gd    # autoload "GameState" — score lives here, not in nodes
  scenes/
    main.tscn        Main (Node2D)
                       ├─ TileMapLayer        # level geometry + physics layer
                       ├─ Player (instance of player.tscn)
                       ├─ Coins (Node2D)      # coin.tscn instances as children
                       └─ HUD (CanvasLayer) ─ ScoreLabel (Label)
    player.tscn      Player (CharacterBody2D) ─ Sprite2D, CollisionShape2D
    coin.tscn        Coin (Area2D) ─ Sprite2D, CollisionShape2D
```

Architecture decisions:
- Score in an autoload singleton (`GameState`) with a typed signal; HUD and coins never reference each other — both talk only to the singleton.
- Gravity read from ProjectSettings so the editor slider (`physics/2d/default_gravity`) stays the single source of truth.
- Coyote time + jump buffering as countdown timers in `_physics_process` (no Timer nodes) — frame-exact and cheap.
- Coin pickup via `Area2D.body_entered`; coin frees itself. Respawn = fall below `kill_y`, reset to the position recorded in `_ready()`.

The core script — `scripts/player.gd` (attach to the Player CharacterBody2D):

```gdscript
class_name Player
extends CharacterBody2D

const SPEED: float = 220.0
const JUMP_VELOCITY: float = -380.0
const COYOTE_TIME: float = 0.12    # grace after walking off a ledge
const JUMP_BUFFER: float = 0.12    # grace for pressing jump before landing

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var coyote_timer: float = 0.0
var buffer_timer: float = 0.0
var spawn_point: Vector2

@export var kill_y: float = 700.0  # falling past this respawns

func _ready() -> void:
	spawn_point = global_position

func _physics_process(delta: float) -> void:
	if is_on_floor():
		coyote_timer = COYOTE_TIME       # refill while grounded
	else:
		velocity.y += gravity * delta
		coyote_timer -= delta

	if Input.is_action_just_pressed("jump"):
		buffer_timer = JUMP_BUFFER       # remember the press
	else:
		buffer_timer -= delta

	if buffer_timer > 0.0 and coyote_timer > 0.0:
		velocity.y = JUMP_VELOCITY
		buffer_timer = 0.0               # consume both windows
		coyote_timer = 0.0

	# variable jump height: releasing early cuts the ascent
	if Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= 0.5

	var direction: float = Input.get_axis("move_left", "move_right")
	if direction != 0.0:
		velocity.x = direction * SPEED
	else:
		velocity.x = move_toward(velocity.x, 0.0, SPEED * 10.0 * delta)

	move_and_slide()

	if global_position.y > kill_y:
		respawn()

func respawn() -> void:
	global_position = spawn_point
	velocity = Vector2.ZERO
```

Note the order inside `_physics_process`: gravity/timers first, jump resolution second, horizontal input third, then a single `move_and_slide()` — never call it twice per frame. `is_on_floor()` reports the result of the *previous* slide, which is exactly what coyote time wants.

---

## `scripts/game_state.gd` — autoload singleton

Register in Project Settings → Globals (Autoload) with node name `GameState`, or add to `project.godot` as shown below. Every script can then reference `GameState` directly.

```gdscript
extends Node

signal score_changed(new_score: int)

var score: int = 0

func add_score(amount: int) -> void:
	score += amount
	score_changed.emit(score)

func reset() -> void:
	score = 0
	score_changed.emit(score)
```

## `scripts/coin.gd` — attach to Coin (Area2D) root of `coin.tscn`

The coin only needs a CollisionShape2D (e.g. CircleShape2D radius 8) and a Sprite2D. `body_entered` fires when a physics body overlaps; type-check against `Player` so tilemap bodies and enemies are ignored.

```gdscript
extends Area2D

@export var value: int = 1

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		GameState.add_score(value)
		queue_free()   # one-shot pickup; freeing also disconnects signals
```

## `scripts/hud.gd` — attach to HUD (CanvasLayer)

CanvasLayer keeps the label fixed on screen regardless of camera movement. The HUD is a pure listener: it renders whatever the singleton says, including the initial value on `_ready`.

```gdscript
extends CanvasLayer

@onready var score_label: Label = $ScoreLabel

func _ready() -> void:
	GameState.score_changed.connect(_on_score_changed)
	_on_score_changed(GameState.score)   # paint initial state

func _on_score_changed(new_score: int) -> void:
	score_label.text = "Coins: %d" % new_score
```

## `scripts/main.gd` — attach to Main (Node2D), optional glue

Resets the run when the scene (re)loads so score never leaks across restarts.

```gdscript
extends Node2D

func _ready() -> void:
	GameState.reset()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):   # Esc restarts the level
		get_tree().reload_current_scene()
```

## `project.godot` — the relevant sections

Godot writes this file for you; these are the entries the editor UI creates. Add the three actions under Project Settings → Input Map, and the autoload under Globals.

```ini
[application]
config/name="MiniPlatformer"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.3")

[autoload]
GameState="*res://scripts/game_state.gd"

[input]
move_left={
"deadzone": 0.5,
"events": [Object(InputEventKey,"physical_keycode":65), Object(InputEventKey,"physical_keycode":4194319)]
}
move_right={
"deadzone": 0.5,
"events": [Object(InputEventKey,"physical_keycode":68), Object(InputEventKey,"physical_keycode":4194321)]
}
jump={
"deadzone": 0.5,
"events": [Object(InputEventKey,"physical_keycode":32)]
}

[physics]
2d/default_gravity=980.0
```

(A = 65, D = 68, Space = 32; the 41943xx codes are the arrow keys. Adding them in the editor UI is easier than hand-writing these objects.)

## Scene assembly checklist

1. **player.tscn** — root `CharacterBody2D` named `Player`, script `player.gd`. Children: `Sprite2D` (any 16–32 px texture; a plain `PlaceholderTexture2D` works), `CollisionShape2D` with a `RectangleShape2D` or `CapsuleShape2D` matching the sprite. Leave Motion Mode = Grounded and Up Direction = (0, -1), the defaults `move_and_slide()` expects for platformers.
2. **coin.tscn** — root `Area2D` named `Coin`, script `coin.gd`. Children: `Sprite2D`, `CollisionShape2D` (CircleShape2D). Monitoring stays on by default, which is what makes `body_entered` fire.
3. **main.tscn** — root `Node2D` named `Main` with `main.gd`. Add a `TileMapLayer`, create a `TileSet` with a physics layer, and paint tiles whose tile physics shapes give the player something to stand on (in Godot 4.2 and earlier the node is `TileMap`; the script code is unchanged). Instance `player.tscn`, then instance several `coin.tscn` under a plain `Node2D` named `Coins` for tidiness. Add `HUD` (CanvasLayer, script `hud.gd`) with a child `Label` named `ScoreLabel` anchored top-left.
4. Add a `Camera2D` as a child of `Player` if the level is wider than the viewport; enable Position Smoothing for a nicer feel.

## Behavior summary

Run the main scene: A/D or arrows move, Space jumps. Walk off a ledge and you can still jump for 0.12 s (coyote); press jump slightly before landing and it fires on touch (buffer); releasing jump early gives a short hop. Touching a coin increments the HUD via `GameState.score_changed`. Falling below `kill_y` snaps the player back to their starting position with velocity zeroed, score intact; Esc reloads the level and resets the score.

## Optional: kill zone as an Area2D instead of `kill_y`

For levels with pits at different heights, replace the `kill_y` check with explicit hazard areas. Make a `killzone.tscn` (root `Area2D`, child `CollisionShape2D` with a wide `WorldBoundaryShape2D` or rectangle) and attach:

```gdscript
extends Area2D

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		body.respawn()
```

This works because `respawn()` is a public method on `Player` — the kill zone drives the player, the player never knows kill zones exist. Delete the `kill_y` check from `player.gd` if you adopt this; keeping both means two respawn paths to debug.

## Optional: checkpoints

Checkpoints are the same pattern as coins — an `Area2D` that mutates state on contact, except the state it mutates is the player's `spawn_point`:

```gdscript
extends Area2D

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		body.spawn_point = global_position
```

## Pitfalls this example already avoids (keep avoiding them)

- **Physics in `_process`.** All movement lives in `_physics_process`; mixing the two causes jitter because rendering and physics tick at different rates. Only cosmetic code (sprite flip, animation selection) may go in `_process`.
- **Calling `move_and_slide()` more than once per frame.** It both moves the body and updates `is_on_floor()`/collision state; a second call double-moves the player.
- **Checking `is_on_floor()` before the first slide.** Its value is stale until `move_and_slide()` has run at least once — harmless here because the timers tolerate one frame of "airborne" at spawn, but do not gate one-shot spawn logic on it.
- **Storing score on the player or HUD.** Either dies with a scene reload; the autoload survives scene changes, which is also what makes a multi-level game work later without refactoring.
- **Direct node paths across scenes** (`get_node("/root/Main/HUD")`). Everything here communicates through the `GameState` signal or a type check (`body is Player`), so scenes can be rearranged freely.
- **Freeing the coin before awarding score.** `queue_free()` defers deletion to end of frame, so the order in `coin.gd` is actually safe either way — but keeping the award first reads as intent.

## Cosmetics: sprite facing and animation

Visual-only reactions belong in `_process`, reading the velocity the physics tick already computed. Add to `player.gd` (assumes an `AnimatedSprite2D` child named `Sprite` with "idle", "run", and "jump" animations):

```gdscript
@onready var sprite: AnimatedSprite2D = $Sprite

func _process(_delta: float) -> void:
	if velocity.x != 0.0:
		sprite.flip_h = velocity.x < 0.0
	if not is_on_floor():
		sprite.play("jump")
	elif velocity.x != 0.0:
		sprite.play("run")
	else:
		sprite.play("idle")
```

`play()` is idempotent when the same animation is already playing, so calling it every frame is fine.

## Tuning notes

- Feel is dominated by three numbers: `SPEED`, `JUMP_VELOCITY`, and gravity. With gravity 980, a jump velocity of -380 gives roughly a 74 px apex (`v² / 2g`); raise gravity and jump velocity together for a snappier arc.
- Coyote/buffer windows of 0.08–0.15 s are the usual range; 0.12 s is generous without feeling floaty.
- The `move_toward` friction factor (`SPEED * 10.0 * delta`) stops the player in about 0.1 s. Lower the multiplier for ice, raise it for instant stops.
- For one-way platforms, enable **One Way Collision** on the tile's physics polygon in the TileSet editor — no player code changes needed; `move_and_slide()` handles it.
