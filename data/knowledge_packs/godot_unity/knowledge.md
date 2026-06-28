# Godot & Unity Game-Engine Reference

## Godot — node + scene tree
- Build from **nodes**; compose into **scenes** (reusable trees saved as `.tscn`).
- Instance at runtime: `var b=preload("res://Bullet.tscn").instantiate(); add_child(b)`.
- GDScript: `extends Node2D`, `@export var speed:=200.0` (Inspector), `$Sprite2D` / `get_node("Sprite2D")` for children.

### Lifecycle
- `_ready()` — init after node enters tree.
- `_process(delta)` — per-frame (UI/non-physics). **Multiply motion by `delta`**.
- `_physics_process(delta)` — fixed-step; do movement here: `velocity=dir*speed; move_and_slide()`.

### Signals (decouple events — don't poll)
```gdscript
signal died
died.emit()
health.died.connect(_on_died)
```
- Free spawned nodes: `queue_free()` (deferred, safe). Leaks come from never freeing.

## Unity — GameObject + Component
- `GameObject` is a container; behavior lives in **Components** (`MonoBehaviour`).
- `[SerializeField] private float speed=5f;` exposes private fields in Inspector.
- **Prefabs**: `Instantiate(prefab,pos,rot);` spawns; `Destroy(go);` removes.

### Lifecycle
- `Awake()`/`Start()` — init. **Cache `GetComponent` here**, never in `Update`.
- `Update()` — per-frame; multiply by `Time.deltaTime`.
- `FixedUpdate()` — physics/Rigidbody (`rb.MovePosition`).

```csharp
Rigidbody rb;
void Awake(){ rb=GetComponent<Rigidbody>(); }
void Update(){ transform.Translate(Vector3.forward*speed*Time.deltaTime); }
```
- Timed work via coroutines: `IEnumerator F(){ yield return new WaitForSeconds(1f);}` -> `StartCoroutine(F())`.

## Shared gotchas -> fix
- **GC spikes**: no per-frame allocation; **pool** objects, cache refs.
- **`GetComponent`/`find` in `Update`**: cache once in init.
- **Movement without delta**: frame-rate dependent -> `FixedUpdate` or `*delta`/`*Time.deltaTime`.
- **Tight coupling**: emit **signals/events**, don't poll.
- **Leaks**: always `queue_free()`/`Destroy()` spawned objects.
- **Heavy per-frame work**: throttle, move off hot path, cache results.
