# Godot 4 & Unity Game-Engine Reference

## Godot 4 — Nodes, Scenes, GDScript
- Build from **nodes**; compose into **scenes** (reusable trees saved as `.tscn`). Scene = prefab equivalent.
- Instance at runtime: `var b = preload("res://Bullet.tscn").instantiate(); add_child(b)`. `preload` at parse time (const path), `load()` at runtime (dynamic path).
- GDScript basics: `extends Node2D`, `@export var speed := 200.0` (Inspector-editable), `@onready var sprite = $Sprite2D` (resolves after tree entry), `get_node("Path/To/Child")`.
- Godot 4 annotations replace Godot 3 keywords: `@export` (was `export`), `@onready` (was `onready`), `@tool` (was `tool`). `instantiate()` was `instance()`; `yield` -> `await`.
- Typed GDScript: `var hp: int = 100`, `func hit(dmg: int) -> void:` — catches errors, faster.
- Unique names: mark node "% Access as Unique Name", then `%Player` from anywhere in the scene.

### Lifecycle
- `_ready()` — after node AND children enter tree (children ready first, bottom-up).
- `_process(delta)` — per-frame (UI, animation, non-physics). Multiply motion by `delta`.
- `_physics_process(delta)` — fixed step (60 Hz default). All movement/physics here: `velocity = dir * speed; move_and_slide()` (Godot 4: `velocity` is a CharacterBody2D/3D property; no args to `move_and_slide`).
- `_input(event)` / `_unhandled_input(event)` — event-driven input; polling via `Input.is_action_pressed("jump")`, `Input.get_vector("left","right","up","down")`.

### Signals (decouple — don't poll)
```gdscript
signal died(cause: String)
died.emit("lava")                # Godot 3: emit_signal("died", ...)
health.died.connect(_on_died)    # Godot 3: connect("died", self, "_on_died")
await get_tree().create_timer(1.0).timeout   # one-shot delay
```
- Signal UP (child emits, parent connects), call DOWN (parent calls child methods). Never `get_parent()` chains.
- Free spawned nodes with `queue_free()` (deferred, safe mid-frame). `free()` immediately — rarely safe.

### Physics & Bodies
- `CharacterBody2D/3D`: scripted movement (`move_and_slide`, `is_on_floor()`). `RigidBody`: engine-simulated — apply forces/impulses, do NOT set position directly (use `_integrate_forces` if you must). `Area2D/3D`: overlap detection (`body_entered` signal), no collision response. `StaticBody`: immovable.
- Collision layers vs masks: **layer** = what I am; **mask** = what I detect.

### Resources & data
- `Resource` subclasses = data containers (like Unity ScriptableObjects): `class_name WeaponData extends Resource` with `@export` fields, saved as `.tres`. Shared by reference — `.duplicate()` for per-instance state.
- Autoloads (Project Settings > Autoload) = singletons for global state/managers; accessible by name.
- Groups: `add_to_group("enemies")`; `get_tree().get_nodes_in_group("enemies")`; `get_tree().call_group("enemies","alert")`.

## Unity — GameObject + Component
- `GameObject` = container; behavior in **Components** (`MonoBehaviour` scripts). Composition over inheritance.
- `[SerializeField] private float speed = 5f;` — Inspector-editable, stays private. Public fields also serialize (avoid). Properties, static, and `Dictionary` do NOT serialize (use paired lists or `[Serializable]` wrapper).
- **Prefabs**: `Instantiate(prefab, pos, rot)`; `Destroy(go)`; `Destroy(go, 2f)` delayed. Prefab overrides on instances; Apply pushes to asset.
- `ScriptableObject`: shared data assets — `[CreateAssetMenu] public class WeaponData : ScriptableObject`. Runtime changes in editor persist to the asset (unlike scene objects); shared by reference across users.

### Lifecycle (order matters)
- `Awake()` — self-init, cache `GetComponent`; runs even if disabled component (not inactive GameObject). No cross-object calls yet.
- `OnEnable()` — subscribe events here; unsubscribe in `OnDisable()` (prevents leaks and missed re-enables).
- `Start()` — before first frame, after all Awakes — safe for cross-object refs.
- `Update()` — per-frame; scale by `Time.deltaTime`. `FixedUpdate()` — physics step (default 0.02 s); all Rigidbody work here (`rb.AddForce`, `rb.MovePosition`) with `Time.fixedDeltaTime`. `LateUpdate()` — after all Updates (camera follow).
```csharp
Rigidbody rb;
void Awake() { rb = GetComponent<Rigidbody>(); }        // cache once, never in Update
void FixedUpdate() { rb.MovePosition(rb.position + dir * speed * Time.fixedDeltaTime); }
```
- Coroutines: `IEnumerator F(){ yield return new WaitForSeconds(1f); }` -> `StartCoroutine(F())`. Stop with `StopCoroutine`; destroyed/disabled GameObject kills its coroutines silently. `yield return null` = next frame; cache `WaitForSeconds` to avoid per-loop alloc.

### Physics & collisions
- `OnCollisionEnter(Collision c)` needs non-kinematic Rigidbody on at least one object. `OnTriggerEnter(Collider c)` needs `isTrigger` checked + a Rigidbody in the pair.
- Never move a physics object via `transform.position` — teleports through walls; use Rigidbody APIs.
- Raycast: `Physics.Raycast(origin, dir, out RaycastHit hit, dist, layerMask)` — always pass a LayerMask.

### Events & decoupling
- C# events/`UnityEvent` for decoupling; `UnityEvent` wires in Inspector. Unsubscribe in `OnDisable`/`OnDestroy` or destroyed listeners throw.
- Null check quirk: destroyed Unity objects compare `== null` (fake null) but are not reference-null — never use `?.` / `??` on UnityEngine.Object.

### Animation & juice
- Godot: `AnimationPlayer` keyframes any property; call `anim.play("run")`. One-off code tweens: `var t = create_tween(); t.tween_property(sprite, "modulate:a", 0.0, 0.5)` (Godot 4 — Godot 3 needed a Tween node).
- Unity: Animator + state machine for characters; for code tweens use `Vector3.Lerp`/`Mathf.MoveTowards` in Update or a tween library (DOTween). `AnimationCurve` fields give designer-editable easing in the Inspector.

## Gotchas -> Fix
- **`GetComponent`/`GetNode`/`Find` in Update/_process**: cache in `Awake`/`_ready`/`@onready`.
- **Movement without delta**: frame-rate dependent -> `* delta` / `* Time.deltaTime`, physics in fixed step.
- **GC/stutter spikes**: no per-frame `new`/string concat/LINQ/closures in hot paths; pool bullets/particles; cache `WaitForSeconds`.
- **Unity: physics in Update / transform moves on Rigidbody**: use `FixedUpdate` + Rigidbody API.
- **Unity: `OnTrigger` never fires**: missing Rigidbody in pair, or `isTrigger` unchecked, or layer collision matrix blocks it.
- **Unity: NullReference on cross-object ref in Awake**: other object may not be awake -> move to `Start()`.
- **Unity: Dictionary/property doesn't show in Inspector**: not serializable -> `[SerializeField]` fields, `[Serializable]` classes, parallel lists.
- **Unity: event subscribed in Start, object re-enabled**: subscribe `OnEnable`, unsubscribe `OnDisable`.
- **Godot: `$Node` null in `_init`**: tree not built -> use `@onready` or `_ready()`.
- **Godot: freeing a node mid-signal crashes**: `queue_free()` not `free()`; guard with `is_instance_valid(node)`.
- **Godot: editing a `.tres` Resource changes all users**: Resources are shared -> `resource.duplicate()` for per-instance data.
- **Godot: RigidBody position set directly**: fights the physics engine -> impulses/forces or `PhysicsServer`/`_integrate_forces`.
- **Godot 3 -> 4 porting**: `KinematicBody` -> `CharacterBody`, `move_and_slide(velocity)` -> property + no-arg call, `yield(obj,"sig")` -> `await obj.sig`, `Spatial` -> `Node3D`.
- **Scene/prefab leaks**: every `Instantiate`/`instantiate()` needs a matching `Destroy`/`queue_free()` path.
- **Tight coupling / polling**: emit signals (Godot) or events (Unity); child never reaches up via `get_parent()`/`transform.parent` assumptions.
- **Editor-only paths in builds** (Godot `res://` writes): `res://` is read-only in export -> write to `user://`.
- **Unity time scale pause breaks coroutines**: `WaitForSeconds` obeys `timeScale` -> `WaitForSecondsRealtime` for UI during pause.

## When to pick which
- Godot: lightweight, open-source, excellent 2D, fast iteration, GDScript or C#. Unity: bigger asset ecosystem, mobile/console pipelines, C# only, heavier editor.
