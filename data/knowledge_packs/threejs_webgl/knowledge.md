# Three.js & WebGL

## Core Setup
```js
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(w, h);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); // cap for perf
document.body.appendChild(renderer.domElement);
```
- Camera at origin looking down -Z by default; move it (`camera.position.set(0,2,5)`) or the scene is invisible.
- Resize handler must update BOTH: `camera.aspect = w/h; camera.updateProjectionMatrix(); renderer.setSize(w,h);`
- Near/far planes: keep near as large as tolerable (0.1, not 0.0001) — tiny near destroys depth precision (z-fighting).

## Animation Loop + Delta
```js
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();       // seconds since last frame
  mixer?.update(dt);                 // GLTF animations
  controls?.update();
  renderer.render(scene, camera);
});
```
- `setAnimationLoop` over raw `requestAnimationFrame` (required for WebXR). Scale ALL motion by `dt` — 144Hz monitors run rAF at 144fps.

## Meshes, Materials, Lights
- `new THREE.Mesh(geometry, material)`; share one geometry/material across many meshes — each unique material = state change.
- `MeshStandardMaterial` (PBR, needs lights), `MeshBasicMaterial` (unlit — renders even with zero lights; use to debug "everything is black").
- Lights: `AmbientLight`/`HemisphereLight` for fill + one `DirectionalLight`. Shadows are opt-in everywhere: `renderer.shadowMap.enabled = true`, `light.castShadow = true`, per-mesh `castShadow`/`receiveShadow = true`.
- DirectionalLight shadows use an ortho camera — set its box (`light.shadow.camera.left/right/top/bottom`) to fit the scene or shadows clip/blur.

## Loading GLTF
```js
const loader = new GLTFLoader();
loader.load('model.glb', (gltf) => {
  scene.add(gltf.scene);
  mixer = new THREE.AnimationMixer(gltf.scene);
  mixer.clipAction(gltf.animations[0]).play();
});
```
- Prefer `.glb` (binary, single file). Draco/Meshopt-compressed assets need their decoder configured on the loader.
- Loaded materials expect correct color management; if the model looks washed out or too dark, check `renderer.outputColorSpace` and texture `colorSpace` settings for your three version.

## Raycasting (Picking)
```js
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
canvas.addEventListener('pointerdown', e => {
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX-r.left)/r.width)*2-1, -((e.clientY-r.top)/r.height)*2+1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(scene.children, true)[0]; // recursive!
});
```
- NDC y is FLIPPED (negate). `intersectObjects(..., true)` for nested GLTF scenes. Intersections are sorted by distance; `hit.object` may be a child mesh — walk `.parent` to find your logical entity.

## Disposing (memory leaks)
- `scene.remove(mesh)` does NOT free GPU memory. Must call `geometry.dispose()`, `material.dispose()`, and `texture.dispose()` on every map the material holds.
- Traverse GLTF scenes to dispose all children; materials can be arrays. `renderer.dispose()` when tearing down the whole canvas (SPA route changes!).
- Check `renderer.info.memory.geometries/textures` — should return to baseline after cleanup.

## Performance
- Draw calls are the usual bottleneck: check `renderer.info.render.calls`. Hundreds is fine, thousands hurts.
- Same mesh many times -> `InstancedMesh` (one draw call for N instances; set per-instance transforms via `setMatrixAt(i, m)` then `instanceMatrix.needsUpdate = true`).
- Static level geometry -> merge with `BufferGeometryUtils.mergeGeometries`.
- Reuse `Vector3`/`Quaternion` temporaries in the loop; `new` per frame churns GC.
- Textures: power-of-two sizes for mipmaps; cap `setPixelRatio` at 2; frustum culling is automatic per-object but not per-merged-vertex.

## ShaderMaterial Basics
```js
new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `uniform float uTime; varying vec2 vUv;
    void main(){ gl_FragColor = vec4(vUv, abs(sin(uTime)), 1.0); }`
});
```
- Three injects `projectionMatrix`, `modelViewMatrix`, attributes `position/uv/normal` automatically. Update uniforms per frame: `mat.uniforms.uTime.value = t` (reassigning the uniforms object breaks the binding).

## Transforms & Scene Graph
- Children inherit parent transforms; `mesh.position` is LOCAL. World position: `mesh.getWorldPosition(new THREE.Vector3())`.
- Rotation options: `mesh.rotation` (Euler, order 'XYZ' default — gimbal lock on combined rotations), `mesh.quaternion` (safe compose), `lookAt(target)` for aiming. Don't mix euler writes and quaternion writes in the same frame — last write wins.
- Group empty `THREE.Group()` as pivot parents to orbit/offset rotation centers instead of recomputing positions.

## Cameras & Controls
- `OrbitControls(camera, renderer.domElement)` for inspection scenes; set `controls.target` and call `controls.update()` in the loop (mandatory if `enableDamping = true`).
- OrthographicCamera for 2D/UI/isometric: define frustum from viewport aspect (`-aspect*s, aspect*s, s, -s`) and update all four on resize, not just aspect.
- Attaching camera as a child of a moving object beats manually copying positions each frame.

## Textures Quick Notes
- `new THREE.TextureLoader().load(url)` is async — material shows black/blank until loaded; fine normally, but sizing logic must wait for the callback.
- `texture.wrapS = texture.wrapT = THREE.RepeatWrapping; texture.repeat.set(4,4)` for tiling; non-repeat-wrapped textures clamp at edges.
- `texture.needsUpdate = true` after mutating a canvas-backed texture, or changes never upload.

## Helpers Worth Knowing
- `new THREE.AxesHelper(5)`, `GridHelper`, `CameraHelper(light.shadow.camera)` (visualize the shadow frustum), `BoxHelper(mesh)` — add temporarily whenever orientation or bounds are in question.
- `stats.js` panel or `renderer.info` logged once per second: draw calls, triangles, geometries, textures — your four perf dials.
- `scene.overrideMaterial = new THREE.MeshBasicMaterial({wireframe:true})` — one line to check whether a problem is geometry or materials/lighting.

## Gotchas -> Fix
- **Black screen**: no light with a lit material, camera inside/at object, or forgot `scene.add`. Fix: swap in `MeshBasicMaterial` + `AxesHelper` to isolate; then add lights/move camera.
- **Model invisible after load**: wrong scale (mm vs m exports) or camera far plane clips it. Fix: `Box3().setFromObject(gltf.scene)` to inspect bounds, rescale/reframe.
- **Memory climbs on scene changes**: removed meshes never disposed. Fix: traverse and dispose geometry/material/textures; verify with `renderer.info.memory`.
- **Raycast misses obvious object**: forgot `recursive=true`, stale NDC (no rect offset), or object scaled via matrix without `updateMatrixWorld`. Fix: as above; call `updateMatrixWorld(true)` if transforming outside the render loop.
- **Z-fighting flicker**: near plane too small or coplanar surfaces. Fix: raise near plane, offset geometry, or `polygonOffset` on the material.
- **Jagged edges**: `antialias: true` must be set at renderer CREATION (can't toggle later); high pixelRatio uncapped kills fps instead. Fix: set at construction, cap ratio.
- **Animations frozen**: forgot `mixer.update(dt)` in the loop or `.play()` on the action. Fix: both; keep the mixer reference alive.
- **Everything too dark/washed out after upgrade**: color-space defaults changed across three versions (sRGB handling). Fix: pin the three version; set `outputColorSpace` explicitly and mark color textures sRGB.
- **fps drops with many identical objects**: one draw call each. Fix: `InstancedMesh` or geometry merging.
- **Canvas stretched/blurry**: CSS size ≠ drawing buffer size. Fix: `renderer.setSize` with real pixel dims (it sets canvas CSS too unless `updateStyle=false`).
