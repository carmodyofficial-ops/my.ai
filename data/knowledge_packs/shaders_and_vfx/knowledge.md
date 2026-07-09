# Shaders & VFX
## Pipeline
- Vertex shader = per-vertex, transforms position object->clip space via MVP matrix (`clip = projection * view * model * vec4(pos,1)`). Fragment shader = per-pixel color. Rasterizer interpolates varyings between them.
- Varyings/interpolators carry data vertex->fragment (uv, normal, world pos, vertex color); perspective-correct by default.
- Uniforms are constant per draw call (time, matrices, params); attributes are per-vertex inputs (position, uv, normal).
- Stage order: vertex -> (tessellation/geometry, optional) -> rasterize -> fragment -> depth/stencil test -> blend -> framebuffer.
## Spaces
- Object/local (mesh authoring), World (scene), View/eye (camera at origin), Clip (post-projection), NDC (-1..1), Screen (pixels).
- Transform normals with the inverse-transpose of the model matrix (not the model matrix) to keep them correct under non-uniform scale.
- Lighting done in world or view space; be consistent. Reconstruct world pos in fragment for effects (fresnel, distance fade).
## UVs & Textures
- UV coords 0..1; sample with `texture(tex, uv)` (GLSL) / `tex2D` (HLSL). Tiling = `uv * scale`; scroll = `uv + time * speed`.
- Wrap modes: repeat, clamp, mirror. Filtering: nearest (pixel art), linear (smooth), trilinear+mipmaps (minification, avoids shimmer).
- Pack data in channels (R=metallic, G=roughness, ...); use `.rgb`/`.a` swizzles.
## Common Effects
- Dissolve: sample noise texture, `clip(noise - threshold)` (or `discard`); animate threshold 0..1; add emissive edge where `noise` near threshold.
- Fresnel/rim: `pow(1 - max(dot(normal, viewDir), 0), power)` -> brighter at grazing angles. Drives rim light, holograms, force fields.
- Outline: (a) inverted-hull — render backfaces scaled along normals in a solid color; (b) post-process edge detect on depth/normal buffer (Sobel).
- Water: scroll two normal maps at different speeds/directions, add for animated ripples; refraction via screen-space UV offset; fresnel for reflection blend; depth-based shoreline foam.
- Toon/cel: quantize `NdotL` into bands via step/ramp texture. Hologram: fresnel + scanlines (`sin(worldPos.y * freq + time)`) + flicker.
## Particle Systems
- Emitter spawns particles with initial position/velocity/lifetime; each simulates then dies. Shape modules: point, cone, sphere, box, mesh.
- Curves-over-lifetime: size, color/alpha, velocity, rotation driven by 0..1 age. Color-over-life alpha fade-out prevents hard pop at death.
- Billboards: quads always facing camera (spherical) or facing but locked to an axis (cylindrical, for beams/trails). Stretched billboards for sparks/rain.
- GPU particles (compute-driven, e.g. Unity VFX Graph, Niagara GPU sim): millions of particles, sim on GPU, but no easy CPU collision/gameplay callbacks. CPU particles: fewer, but collision events, sub-emitters, gameplay hooks.
- Soft particles: fade alpha near opaque geometry (compare particle depth to scene depth) to hide hard intersection seams.
- Flipbook/sprite-sheet animation for explosions/smoke; blend frames for smoothness.
## Performance
- Overdraw: many transparent/particle layers shading the same pixels -> fill-rate bound. Fix: smaller particles, fewer layers, cap emission, use opaque where possible.
- Draw calls / batching: share materials; use GPU instancing for repeated meshes; texture atlases to merge materials. Fewer state changes = fewer calls.
- Fragment cost: heavy math per pixel is expensive at high res. Move constant work to vertex shader or precompute in textures/LUTs.
- Alpha blend can't early-Z; sort transparents back-to-front (correctness) — costs CPU. Alpha test/`discard` disables early-Z on some GPUs (mobile especially).
- Mobile: minimize dependent texture reads, avoid `discard`, prefer half/mediump precision, keep texture fetches low.
## Lighting & Blending Basics
- Blinn-Phong: diffuse = `max(dot(N,L),0)`, specular = `pow(max(dot(N,H),0), shininess)` with half-vector `H = normalize(L+V)`. PBR: metallic-roughness workflow, energy-conserving BRDF, IBL from cubemaps.
- Blend modes: alpha `src.a*src + (1-src.a)*dst`; additive `src + dst` (fire, glow, no depth write, order-independent-ish); multiply darkens. Additive great for particles.
- Premultiplied alpha avoids dark fringing at edges vs straight alpha; be consistent with your texture authoring.
- Gamma/linear: do lighting math in linear space, convert to sRGB for display. Mixing spaces -> washed-out or too-dark results.
## More Effects
- Vertex displacement: offset position in vertex shader by a texture/noise (waves, flags, wind sway). Cheap animated geometry, but shadows/collision won't follow unless matched.
- Distortion/heat haze: sample a normal/noise map, offset the screen-grab UVs by it -> refraction shimmer.
- Trails/ribbons: generate a strip mesh along motion history; UV along length, fade alpha over age.
- Decals: project a texture onto surfaces (bullet holes, blood); screen-space or mesh decals; watch for depth acne on projection.
## Debugging Shaders
- Output intermediate values as color to isolate the broken stage: `gl_FragColor = vec4(uv, 0, 1)` (check UVs), `vec4(normal*0.5+0.5,1)` (check normals), `vec4(vec3(depth),1)`.
- No printf on GPU — visualize. Use frame debuggers: RenderDoc, Unity Frame Debugger, Xcode/PIX. Inspect per-draw inputs, textures, uniforms.
## Gotchas -> Fix
- **Shader compiles but renders black**: unset/zero uniform, wrong space, or normal not normalized. Fix: output uv/normal as color to debug stage-by-stage; verify uniforms are bound and non-zero.
- **Renders magenta/pink (Unity)**: shader failed to compile or material lost its shader. Fix: check console for compile errors, reassign shader, check platform keywords.
- **Normals look wrong under scaling**: used model matrix on normals. Fix: use inverse-transpose of model, and `normalize()` in the fragment shader (interpolation shortens them).
- **Transparency sorting artifacts** (things draw in wrong order): back-to-front sort failing or writing depth. Fix: disable depth write for transparents, sort by distance, or use OIT/alpha-to-coverage.
- **UV seams / texture stretching**: bad UV layout or wrap mode. Fix: check UV unwrap, set clamp vs repeat correctly, add padding in atlases.
- **Particles pop in/out harshly**: no alpha fade over lifetime or hard geometry intersection. Fix: color-over-life alpha ramp; enable soft particles (depth fade).
- **Effect looks right in editor, breaks on mobile/other GPU**: precision (highp vs mediump), unsupported feature, or `discard` cost. Fix: qualify precision, provide fallbacks, avoid dependent reads.
- **Time-based animation stutters**: using frame count not delta-accumulated time, or precision loss in large `time` uniform. Fix: feed continuous time, use `fract`/mod to keep values small.
- **Fresnel/rim wrong**: normal or viewDir in mismatched space, or normal not normalized. Fix: compute both in world space, normalize before `dot`.
- **Huge frame drop with particles**: overdraw from big overlapping transparent quads. Fix: shrink particles, reduce count, lower texture res, LOD emission by distance.
- **Colors look washed out / too dark**: gamma/linear mismatch. Fix: keep textures sRGB flagged, do math in linear, output sRGB; check color space settings.
- **Additive particles vanish on bright backgrounds**: additive adds to a maxed-out framebuffer. Fix: expected — use alpha-blend variant on bright scenes or HDR/bloom pipeline.
- **Dark edges around cutout textures**: straight-alpha bleeding. Fix: use premultiplied alpha or dilate/pad texture edges.
- **Displaced mesh clips through ground / no shadow**: only vertex positions moved. Fix: match collision/shadow pass to the same displacement, or accept and mask.
- **Decals show depth acne / project through walls**: no angle/depth clamp. Fix: clamp by surface normal angle, use depth bias, limit projection box.
