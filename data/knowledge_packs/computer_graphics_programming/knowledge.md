# Computer Graphics Programming Reference

## Rasterization Pipeline (GPU, real-time)
- Stages: **Vertex data** → **Vertex shader** (per-vertex, applies MVP, outputs clip-space position) → **Primitive assembly** (triangles) → **Clipping** (to view frustum) → **Perspective divide** (÷w → NDC) → **Viewport transform** (→ pixels) → **Rasterization** (triangles → fragments, interpolates attributes) → **Fragment/pixel shader** (per-pixel color, lighting, texturing) → **Per-fragment ops** (depth test, stencil, blending) → framebuffer.
- Vertex attributes (position, normal, UV, color) interpolated across the triangle with **perspective-correct interpolation** (dividing by w).
- Programmable stages: vertex, (tessellation control/eval, geometry — optional), fragment, compute. Fixed-function: clipping, raster, depth/blend.

## Transforms & Coordinate Spaces
- Pipeline of spaces: **Model/Object** → (model matrix) → **World** → (view matrix) → **View/Camera/Eye** → (projection matrix) → **Clip** → (÷w) → **NDC** → (viewport) → **Screen**.
- **MVP**: `clip = Projection * View * Model * vec4(pos, 1.0)`. Because matrices are column-major (GLSL) and multiply right-to-left, the model applies first, then view, then projection.
- Model matrix = T * R * S (translate * rotate * scale) — applied to a vertex as S first, then R, then T (rightmost acts first).
- **View matrix** = inverse of the camera's world transform (move the world opposite the camera). `lookAt(eye, center, up)` builds it.
- **Projection**: perspective (frustum, foreshortening, `perspective(fovy, aspect, near, far)`) vs orthographic (parallel, no foreshortening). Both map the view volume into the [-1,1] (or [0,1] depth in D3D/Vulkan) NDC cube and set `w` for the divide.
- **Normals** transform by the **inverse-transpose** of the model matrix (`mat3(transpose(inverse(model)))`) — NOT the model matrix — so non-uniform scale doesn't skew them. Re-normalize after.

## Rasterization vs Ray Tracing
- **Rasterization**: for each triangle, find covered pixels. Fast, hardware-native, great for real-time; global effects (shadows, reflections, GI) need extra passes/tricks (shadow maps, SSR, SSAO, cube maps).
- **Ray tracing**: for each pixel, shoot a ray into the scene, find nearest hit, shade. Natural shadows/reflections/refraction.
  - **Whitted / classic ray tracing**: recursive rays for mirror reflection + refraction + shadow rays to point lights. No soft/indirect lighting.
  - **Path tracing**: Monte Carlo integration of the rendering equation — bounce rays randomly, average many samples per pixel; converges to physically correct global illumination but is noisy (needs denoising / many samples).
  - Acceleration via **BVH** (bounding volume hierarchy) to avoid testing every triangle.

## Lighting & Shading
- **Phong (empirical)**: `color = ambient + diffuse + specular`.
  - Diffuse (Lambert): `kd * max(dot(N, L), 0)`.
  - Specular (Phong): `ks * pow(max(dot(R, V), 0), shininess)` where `R = reflect(-L, N)`. Blinn-Phong uses half-vector `H = normalize(L+V)`, `pow(dot(N,H), s)` — cheaper, better highlights.
- **PBR (physically based)**: energy-conserving, parameterized by base color, **metallic**, **roughness**, normal. Uses a **BRDF** (bidirectional reflectance distribution function) — Cook-Torrance: `D*F*G / (4 (N·L)(N·V))` where D = normal distribution (GGX/Trowbridge-Reitz), F = Fresnel (Schlick approx `F0 + (1-F0)(1-cosθ)^5`), G = geometry/shadowing-masking. Metals: F0 = base color, no diffuse; dielectrics: F0≈0.04.
- Normals must be normalized per-fragment; light/view vectors in a consistent space (usually world or view).

## Texturing & Mipmaps
- UV coords [0,1] map texels to fragments. Wrap modes: repeat, clamp, mirror. Filtering: nearest (blocky) vs bilinear (smooth) vs trilinear (blends mip levels).
- **Mipmaps**: precomputed downscaled chains (1/2, 1/4, …). GPU picks the level by screen-space UV derivatives — fixes **minification aliasing/shimmer** on distant textures and improves cache/perf. **Anisotropic filtering** fixes blur on grazing-angle surfaces.
- Texture types: albedo/diffuse (sRGB), normal map (tangent-space, linear), roughness/metallic/AO (linear), cube maps (environment), 3D textures.

## Depth, Culling, Visibility
- **Z-buffer / depth buffer**: per-pixel nearest depth; fragment passes if closer. Enables arbitrary draw order for opaque geometry. Depth is **non-linear** (more precision near the camera) → z-fighting far away.
- **Back-face culling**: skip triangles facing away (winding order CCW/CW + `dot(N, viewDir)`); ~halves fragment work for closed meshes.
- **Frustum culling**: skip objects outside the camera frustum (CPU-side). **Occlusion culling**: skip objects hidden behind others.
- Transparency: sort back-to-front and blend (`src_alpha, 1-src_alpha`) with depth-write off — Z-buffer alone can't order transparency correctly.

## Graphics APIs — Tradeoffs
- **OpenGL / WebGL**: state-machine, driver-managed, easiest to learn; higher CPU overhead, single-threaded submission; legacy. WebGL = GL ES in the browser.
- **Vulkan / D3D12 / Metal**: explicit, low-level — you manage memory, command buffers, synchronization (barriers, fences, semaphores), pipeline state objects. Much lower CPU overhead, multithreaded command recording, better for AAA/high-draw-call scenes; far more code.
- **WebGPU / WGSL**: modern portable API (browser + native via Dawn/wgpu); explicit-ish but safer than Vulkan; compute shaders; the successor to WebGL.
- Shading languages: **GLSL** (GL/Vulkan), **HLSL** (D3D, also compiles to SPIR-V), **WGSL** (WebGPU), **MSL** (Metal). Vulkan consumes **SPIR-V** bytecode.

## Shaders (GLSL stages)
- **Vertex shader**: runs per vertex; must write `gl_Position` (clip space); passes varyings (`out`) to fragment.
- **Fragment shader**: runs per fragment; writes color (`out vec4`). Has access to interpolated varyings, uniforms, samplers (`texture(sampler, uv)`).
- Uniforms = per-draw constants (matrices, light params); attributes/`in` (vertex) = per-vertex; varyings = interpolated vertex→fragment. UBOs/SSBOs for bulk data. Compute shaders for general GPU work.

## Gotchas -> Fix
- **Matrix multiplication order wrong (objects vanish/skew)** -> in GLSL (column-major) build `P*V*M` and multiply the vector on the right; the rightmost transform applies first. Row-major libraries (DirectXMath) reverse the order.
- **Coordinate handedness / winding mismatch** -> OpenGL is right-handed, +Y up, NDC z ∈ [-1,1]; D3D/Vulkan/Metal use z ∈ [0,1] and often left-handed / flipped Y. A flipped projection or import breaks culling and depth — set correct winding + clip-space convention.
- **Everything too dark or washed out (gamma)** -> do lighting in **linear** space; textures authored in sRGB (albedo) must be decoded to linear on read and the final image encoded back to sRGB on write. Sample color textures as sRGB, keep normal/roughness/data maps linear.
- **Z-fighting (flickering coplanar surfaces)** -> depth precision is non-linear; pull the near plane out (don't set near≈0), use a smaller near/far ratio, apply polygon offset/depth bias, or a reversed-Z / logarithmic depth buffer.
- **Normals wrong after scaling** -> transform normals by the inverse-transpose of the model matrix and re-normalize; using the plain model matrix skews them under non-uniform scale.
- **Specular/lighting looks wrong** -> mixing spaces (light in world, normal in view). Keep N, L, V in the same space; normalize all of them per-fragment.
- **Texture shimmer/aliasing in the distance** -> generate and use mipmaps (`glGenerateMipmap` / trilinear filtering); enable anisotropic filtering for grazing angles.
- **Transparent objects render in wrong order** -> the Z-buffer can't sort blending; draw opaque first (depth write on), then transparent back-to-front with depth write off, or use order-independent transparency.
- **Perspective divide forgotten / w ignored** -> output clip-space `vec4` with correct `w`; the GPU divides by w. Doing lighting in clip space or normalizing positions breaks perspective.
- **Back-face culling hides or shows the wrong faces** -> match cull face mode to your winding order (CCW front-facing by default in GL); disable culling for double-sided/transparent geometry.
- **Ray tracer too noisy** -> path tracing needs many samples per pixel + importance sampling + a denoiser; low sample counts give grain, not a bug.
