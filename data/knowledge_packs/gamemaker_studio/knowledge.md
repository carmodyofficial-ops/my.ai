# GameMaker Studio 2 / GML Reference

## Objects, Instances, Events
- **Object** = a template/class. **Instance** = a runtime copy placed in a room (each has its own variables). `object_index` = the object type; `id` = the unique instance id.
- Instances run **events** (code triggered by the engine), not a `main()`:
  - **Create** — once when the instance spawns; init instance vars here (`hp = 100;`).
  - **Step** — every frame (default 60/s = game speed). Logic, input, movement. Sub-events: Begin Step, Step, End Step (run in that order across all instances).
  - **Draw** — every frame for rendering. If you write ANY Draw event you REPLACE the automatic sprite draw — call `draw_self()` to restore it. Draw GUI event draws in screen space (unaffected by view/camera).
  - **Alarm[0..11]** — countdown timers: set `alarm[0] = 30;` (frames); fires the Alarm 0 event at 0.
  - **Collision(obj)**, **Destroy**, **Clean Up** (runs even on room end/game end — free memory here), Room Start/End, Async events.
- Built-in instance vars: `x, y`, `hspeed/vspeed`, `speed/direction`, `image_index/image_speed`, `image_xscale/yscale/angle/blend/alpha`, `sprite_index`, `depth` (lower = drawn on top), `visible`, `solid`, `persistent`.

## GML Language Basics
- Dynamically typed; `var` = local to the event (dies at event end); no `var` = instance variable (persists); `global.x` = global.
```gml
var _dx = 0;
if (keyboard_check(vk_right)) _dx += 4;
x += _dx;
hp -= 10;
if (hp <= 0) instance_destroy();
```
- `with (obj_or_id) { ... }` changes scope so `x`, `hp`, etc. refer to the target instance(s). `with(obj_enemy) hp -= 5;` hits ALL enemies; `other` refers back to the caller.
- Ternary, `repeat(n){}`, `for/while/do`, `switch`, `#macro NAME value`, `enum State {IDLE, RUN}`.

## Rooms & Layers
- **Room** = a level/screen. **Layers** organize content and draw order (higher layer depth drawn first/behind): Instance layers, Tile layers, Background layers, Asset layers, Path layers.
- Move between rooms: `room_goto(rm_level2)`, `room_goto_next()`, `room_restart()`. `persistent` instances survive room change.
- Cameras/views: `view_camera[0]`, `camera_set_view_pos`, `camera_set_view_target(id)`; the room can be larger than the view (scrolling).

## Sprites, Sequences, Animation
- Sprites = frame sets with an origin (pivot) + collision mask. `image_index` = current frame, `image_speed` = frames advanced per step (1 = normal; set 0 to freeze).
- `sprite_index = spr_run;` swaps animation. `image_number` = frame count. `draw_sprite_ext(spr, sub, x, y, xs, ys, rot, col, alpha)` for manual draws.
- **Sequences** = timeline-based animation/cutscene assets (keyframed sprites, sounds, moments).

## Collision
- `place_meeting(x, y, obj)` — would this instance collide at (x,y) with obj? (the workhorse for movement checks; test the target position BEFORE moving).
```gml
if (!place_meeting(x + hsp, y, obj_wall)) x += hsp;
else while (!place_meeting(x + sign(hsp), y, obj_wall)) x += sign(hsp);
```
- `instance_place(x,y,obj)` returns the colliding instance id (or noone). `position_meeting`, `point_in_rectangle`.
- Bounding box: `bbox_left/right/top/bottom`. Collision masks: precise (per-pixel, slow), rectangle, ellipse, diamond — set on the sprite.
- `collision_line`, `collision_rectangle`, `collision_circle` for area queries.

## Instance Management
- Create on a layer: `instance_create_layer(x, y, "Instances", obj_bullet)` (returns id; you can set vars on it: `var b = instance_create_layer(...); b.speed = 8;`). `instance_create_depth(x,y,depth,obj)` avoids needing a named layer.
- `instance_destroy()` (self, runs Destroy+CleanUp), `instance_destroy(id)`, `instance_exists(obj)`, `instance_number(obj)` (count), `instance_nearest(x,y,obj)`, `instance_find(obj, n)`.
- **Deactivation** for perf/pausing: `instance_deactivate_all(true)`, `instance_activate_object(obj)`, `instance_deactivate_region(...)`. Deactivated instances don't run events or draw but still exist.

## Structs & Methods
- Structs (lightweight objects, GC'd): `var s = { hp: 100, name: "orc" };` access `s.hp`. `new Constructor()`:
```gml
function Vec2(_x, _y) constructor {
    x = _x; y = _y;
    static add = function(o) { return new Vec2(x+o.x, y+o.y); };
}
```
- Methods: `var f = method(self, some_func);` binds scope. Functions are first-class values.

## Data Structures (ds_*) — MUST free manually
- `ds_list`, `ds_map`, `ds_grid`, `ds_stack`, `ds_queue`, `ds_priority`. These are NOT garbage collected.
```gml
inventory = ds_list_create();
ds_list_add(inventory, "sword");
// in Clean Up event:
ds_list_destroy(inventory);
```
- Prefer modern GML arrays (`var a = []; array_push(a, x);`) and structs where possible — they ARE garbage collected, unlike ds_*.

## State Machines
- Enum + switch in Step, or function-per-state stored in a variable:
```gml
enum St { IDLE, RUN, ATTACK }
switch (state) {
    case St.IDLE:   if (abs(hsp) > 0) state = St.RUN; break;
    case St.RUN:    /* move */ break;
}
```

## Shaders (GLSL ES)
- Vertex + fragment shader pairs (`shader_*`). `shader_set(sh_grayscale); draw_self(); shader_reset();`. Pass uniforms: `shader_get_uniform`, `shader_set_uniform_f`; samplers via `shader_get_sampler_index` + `texture_set_stage`.
- Surfaces (`surface_create`, `surface_set_target`, `draw_surface`, `surface_free`) for render-to-texture; surfaces are VOLATILE — can be freed by the OS, always check `surface_exists()` and recreate.

## Gotchas -> Fix
- **`ds_*` memory leak** -> ds structures are never auto-freed; call `ds_*_destroy()` in the **Clean Up** event (not Destroy alone — Clean Up also runs on room/game end). Prefer arrays/structs which ARE garbage collected.
- **Sprite stops drawing after adding a Draw event** -> any Draw event overrides the default sprite render; add `draw_self();` (or `draw_sprite_ext`) inside it.
- **Heavy per-frame cost in Draw** -> `draw_text`/`draw_sprite`/`surface` churn and constant texture-page swaps break batching. Minimize Draw work, group same-texture draws, precompute in Step, use Draw GUI only for HUD.
- **Deactivated instance still "exists" but code fails** -> `instance_deactivate_*` stops events/collision but the instance persists; `instance_exists` on the type may miss deactivated ones. Reactivate before interacting.
- **Global vs instance vs local confusion** -> `var x` dies at event end; bare `x` is per-instance; `global.x` is shared. Reading a `var` in another event = undefined-variable crash. Declare persistent state in Create.
- **`with` scope surprises** -> inside `with(target)`, `x` is the target's; use `other.x` to reach the caller. `with(obj_x)` affects EVERY instance of obj_x.
- **Surface disappeared / black** -> surfaces are volatile (freed on window resize/alt-tab). Always `if (!surface_exists(surf)) surf = surface_create(w,h);` before use.
- **Collision missed at high speed** -> tunneling; check `place_meeting(x+hsp, y, wall)` at the target position and step-approach with `sign()`, or use `collision_line` between old and new position.
- **`instance_create` on nonexistent layer crashes** -> layer name must exist in the room; use `instance_create_depth` to avoid the dependency, or ensure the layer exists.
- **Alarm never fires** -> alarms only count down while the instance is active and the value is > 0; set `alarm[0] = frames` and don't reset it every step.
- **Reading another instance's var when it may be destroyed** -> guard with `if (instance_exists(target))` before `target.hp`; a dangling id throws.
- **Depth vs layer ordering fight** -> setting instance `depth` overrides its layer's draw order; pick one system (layers OR manual depth) and stay consistent.
