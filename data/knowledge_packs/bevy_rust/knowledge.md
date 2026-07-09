# Bevy (Rust Game Engine) Reference

## ECS Core — Entities, Components, Systems
- **Entity** = a lightweight ID (`Entity`, generational index). Holds no data itself.
- **Component** = a plain data struct attached to an entity: `#[derive(Component)] struct Velocity(Vec3);`. Composition, not inheritance.
- **System** = a plain `fn` that reads/writes the `World` via parameters; scheduled by the App. Bevy injects params by type:
```rust
fn movement(time: Res<Time>, mut q: Query<(&mut Transform, &Velocity)>) {
    for (mut tf, vel) in &mut q {
        tf.translation += vel.0 * time.delta_secs();
    }
}
```
- **World** = the container of all entities, components, resources. Systems are just structured access to it.
- **Query** = typed iteration over entities matching a component signature:
  - `Query<(&A, &mut B)>` — entities that have both A and B.
  - Filters: `Query<&Transform, With<Player>>`, `Without<Enemy>`, `Query<Entity, Added<Health>>`, `Changed<T>` (change detection), `Or<(With<A>, With<B>)>`.
  - `q.get(entity)`, `q.single()` / `q.single_mut()` (exactly one match), `q.iter()`, `&mut q` to iterate mutably.

## App, Plugins, Schedules
- Entry point builds an `App`:
```rust
App::new()
    .add_plugins(DefaultPlugins)
    .insert_resource(Score(0))
    .add_systems(Startup, setup)
    .add_systems(Update, (movement, collide).chain())
    .run();
```
- **Plugins** = reusable bundles of systems/resources (`impl Plugin`). `DefaultPlugins` = windowing, render, input, audio, assets, etc. Split your game into plugins.
- **Schedules** replace old fixed "stages": built-in `Startup` (once), `Update` (every frame), `FixedUpdate` (fixed timestep — physics), `PreUpdate`/`PostUpdate`, plus render schedules. `FixedUpdate` uses `Time<Fixed>`; `Update` uses variable frame delta.
- Bevy versions churn hard — the `Stage`/`SystemSet`/`add_system` API changed repeatedly (`add_systems(Schedule, ...)` is current; old `add_system_to_stage` is gone). Pin the exact version; check migration guide.

## Resources vs Components
- **Resource** = a single global singleton value: `#[derive(Resource)] struct Score(u32);` accessed via `Res<Score>` / `ResMut<Score>`. Use for globals (time, asset servers, config, game state).
- **Component** = per-entity data, accessed via `Query`. Rule: many-of → component; one-of → resource.
- `Local<T>` = per-system persistent state (not shared).

## Bundles & Spawning
- **Bundle** = a set of components inserted together. Prefer tuples now: `commands.spawn((Transform::default(), Velocity(v), Player))`. Derive `#[derive(Bundle)]` for named reusable groups.
- `Commands` = deferred structural changes (spawn/despawn/insert/remove) applied at schedule sync points, not immediately:
```rust
fn spawn(mut commands: Commands) {
    let e = commands.spawn((SpriteBundle::default(), Enemy)).id();
    commands.entity(e).insert(Health(100));
    commands.entity(e).despawn();
}
```

## Change Detection & Events
- Automatic: `Changed<C>` / `Added<C>` query filters, and `Res<T>::is_changed()`. Mutating through `&mut` or `ResMut` flags the change (even if you don't actually change the value — deref-mut triggers it).
- **Events** = decoupled messaging. Define `#[derive(Event)] struct Damage{...}`; write via `EventWriter<Damage>`, read via `EventReader<Damage>`. Events live ~2 frames (double-buffered) — a reader must run each frame or miss them; ordering of writer-before-reader matters.

## Systems Ordering & Parallelism
- Systems run **in parallel by default** — Bevy schedules any two systems concurrently unless their data access conflicts (two `&mut` to same component, or `&mut` vs `&`). No shared mutable = automatic parallelism.
- Force order: `.chain()` (run tuple in sequence), `.before(sys)`, `.after(sys)`, `SystemSet` grouping with `.configure_sets(...)`. `.run_if(condition)` for run conditions (states, resource checks).
- **States**: `#[derive(States)]` enum + `add_systems(OnEnter(GameState::Playing), ...)`, `.run_if(in_state(...))` to gate systems.

## Assets & Handles
- `AssetServer` (a resource) loads by path async: `let tex: Handle<Image> = asset_server.load("player.png");`. `load()` returns a **`Handle<T>` immediately**; the actual asset arrives later.
- `Assets<T>` resource holds loaded data; `assets.get(&handle)` returns `Option` (None until loaded). Handles are ref-counted — asset unloads when last strong handle drops (`Handle::Weak` doesn't keep alive).
- Watch load state via `AssetServer::load_state` or `AssetEvent<T>` events.

## Rendering Pipeline (overview)
- Built on `wgpu` (Vulkan/Metal/DX12/WebGPU backend). Render runs in a separate **render world**; the main world's entities are **extracted** into it each frame (extract → prepare → queue → render phases).
- 2D: `Sprite`/`SpriteBundle`, `Camera2d`. 3D: `Mesh3d`/`MeshMaterial3d`, `StandardMaterial` (PBR), `Camera3d`, `DirectionalLight`/`PointLight`. Custom shaders via `Material` trait + WGSL.
- Cameras are entities with a `Camera` component + projection + transform.

## Transforms, Hierarchy, Input, Time
- `Transform` (local, relative to parent) vs `GlobalTransform` (world, computed by the transform propagation system). Never write `GlobalTransform` — set `Transform`; the engine derives global each frame.
- Parenting: `commands.spawn(...).add_child(child)` or `.with_children(|p| { p.spawn(...); })`. Child `Transform` is relative to the parent; despawning a parent needs `despawn_recursive()` to also remove children (plain `despawn` orphans them).
- Input as resources: `Res<ButtonInput<KeyCode>>` (`.pressed()`, `.just_pressed()`), `Res<ButtonInput<MouseButton>>`, gamepad; mouse motion via `EventReader<MouseMotion>`. Window/cursor via `Query<&Window>`.
- Time: `Res<Time>` → `time.delta_secs()` (variable), `Res<Time<Fixed>>` in `FixedUpdate`. Scale all movement by delta for frame-rate independence.

## Gotchas -> Fix
- **`Query` borrow conflict panic ("conflicting access")** -> two params access the same component mutably. Split with `Without<T>` filters, or combine into one query, or use `ParamSet<(Query<...>, Query<...>)>` to alias safely.
- **Structural change didn't happen this frame** -> `Commands` are deferred to the next sync point; if a later system in the same schedule needs the entity, `.chain()` after the spawner or add an explicit `apply_deferred`/sync.
- **`query.single()` panics** -> it requires exactly one match; use `get_single()`/`single().ok()` and handle 0-or-many, or ensure the marker component is unique.
- **Events missed / never received** -> reader system didn't run that frame, or ran before the writer; events double-buffer (~2 frames). Order writer `.before` reader, and ensure the reader runs every frame.
- **`Changed<T>` fires every frame unexpectedly** -> any `&mut`/`ResMut` deref flags a change even without a real modification. Only take mutable access when actually mutating.
- **Asset `get()` returns None right after `load()`** -> loading is async; the `Handle` is valid but data lands later. Gate on `AssetEvent`/load state, or design systems to tolerate not-yet-loaded.
- **Two systems that should be ordered run in random order** -> parallel by default; add `.chain()`, `.before()`, `.after()`, or a `SystemSet`. Don't rely on registration order.
- **Handle dropped → texture/mesh vanishes** -> a `Handle<T>` is ref-counted; store it in a component/resource to keep the asset alive. A `Weak` handle won't.
- **Code from a tutorial won't compile** -> Bevy's API breaks between minor versions (`add_system`→`add_systems`, stages→schedules, `Bundle` structs→tuples, `delta_seconds`→`delta_secs`). Match the tutorial's Bevy version or consult the migration guide.
- **Borrow checker fights ECS lifetimes** -> don't hold a `&mut World` and query simultaneously; use system params. For nested/scoped access use `World::resource_scope` or `SystemState`.
- **Component not found / query empty** -> spawn inserted the wrong bundle, or a `With<Marker>` filter excludes it; verify the entity actually has every queried component (missing one silently drops the entity from the query).
- **`Res<T>` panics "resource does not exist"** -> you queried a resource never inserted; `insert_resource`/`init_resource` in a plugin's `build` or before the system runs.
