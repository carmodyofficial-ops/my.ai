# AR / VR / XR Development Reference

## VR Fundamentals
- **Stereo rendering**: render the scene twice, once per eye, from slightly offset camera positions (eye separation ≈ **IPD**, interpupillary distance, ~63mm avg) → binocular depth. Each eye gets its own view + projection matrix and half the display.
  - **Single-pass / multiview** stereo rendering issues both eyes in one draw (instanced) — ~2x CPU savings over two full passes; prefer it.
- **6DoF** (six degrees of freedom): position (x,y,z) + orientation (pitch/yaw/roll) tracked for HMD and controllers. **3DoF** = rotation only (old mobile VR / gaze). Room-scale needs 6DoF.
- **Tracking**: inside-out (cameras on the headset track the environment — Quest, Vision Pro; no external sensors) vs outside-in (external base stations — Lighthouse/Vive). Controllers tracked via IR LEDs / IMU fusion / cameras.
- **Lens distortion**: HMD optics distort the image; the runtime applies **barrel distortion + chromatic aberration correction** as a post pass so it looks correct through the lenses. Don't fight it.

## Performance — the #1 constraint
- **Target framerate is non-negotiable**: 72/80/90/120 Hz depending on device; missing it causes judder and **motion sickness**. Budget: ~11ms/frame at 90Hz for EVERYTHING (both eyes). Standalone (Quest) is a mobile GPU — treat like a phone.
- **Motion-to-photon latency** (head move → updated photons on screen) must be low (<20ms). Achieved via high framerate + prediction + **reprojection/timewarp** (ASW/ATW — the runtime re-warps the last frame to the latest head pose so tracking stays responsive even if a frame is dropped). Reprojection masks drops but is a safety net, not a budget.
- **Foveated rendering**: render full resolution only where the eye looks (fixed foveated = center; **eye-tracked foveated** = gaze-driven) and lower res in the periphery → big GPU savings. Use on Quest Pro / Vision Pro / PSVR2.
- Optimize like mobile: draw calls low (batching/instancing), forward/single-pass rendering, baked lighting, MSAA over post-AA, aggressive LODs, avoid full-screen post-processing and heavy transparency/overdraw.

## Locomotion & Comfort
- **Teleport** locomotion = point-and-blink; most comfortable (no vestibular mismatch), default for wide audiences.
- **Smooth/continuous** locomotion causes sickness (visual motion without physical motion). Mitigate with: **vignette / tunneling** (narrow FOV during movement), snap-turn (discrete rotation instead of smooth yaw), reduced acceleration, a stable horizon/nose reference.
- **Motion sickness** root cause = **sensory conflict** (eyes see motion the inner ear doesn't feel), worsened by low framerate, latency, acceleration, and artificial camera moves. Never move the camera the player didn't cause; never add head-bob or forced FOV changes.
- Keep a stable ground plane and horizon; avoid stairs/inclines with smooth locomotion.

## Interaction
- **Controllers**: 6DoF tracked, with buttons/triggers/grip/thumbstick + haptics. Map grab to grip. Provide haptic + visual feedback on every interaction.
- **Raycasts / pointers**: laser pointer from the controller for distant UI/selection (`Physics.Raycast` from controller pose along forward). Near = direct/poke.
- **Grabbing**: attach the object to the hand pose on grip-down (snap to a grab pose or free-grab at contact point), release on grip-up (impart controller velocity for throwing). Use kinematic while held; restore physics on release.
- **Hand tracking**: cameras estimate finger joints (no controller) → pinch = select, direct poke of UI. Less precise/reliable than controllers (lighting-dependent, occlusion) — offer both; use large targets.
- **Eye/gaze**: for foveation, UI hover, or gaze-and-pinch selection (Vision Pro's core input model).

## AR Fundamentals
- **World/motion tracking**: **SLAM** (Simultaneous Localization And Mapping) — fuses camera + IMU (VIO, visual-inertial odometry) to track device pose and build a map of the environment in real time.
- **Plane detection**: find horizontal/vertical surfaces (floors, tables, walls) to place content on.
- **Anchors**: pin virtual content to a real-world point so it stays put as you move; **cloud/shared anchors** (ARCore Cloud Anchors, ARKit/Azure Spatial Anchors) enable persistence and multi-user co-location.
- **Occlusion**: real objects should hide virtual ones — needs a depth map (LiDAR on Pro iPhones/iPad, or ML depth estimation, or people/hand occlusion). Without it, holograms float unconvincingly in front of everything.
- **Lighting estimation**: sample real ambient light/color/direction so virtual objects match the scene. **Environment probes** for reflections.
- **Passthrough** (Quest/Vision Pro) = MR: cameras show the real world with virtual content composited in.

## Platforms & SDKs
- **OpenXR**: the cross-vendor standard API (Khronos); target it to run on Quest, SteamVR, Vision Pro (limited), Windows MR, etc. — avoids per-vendor lock-in. Extensions expose device-specific features.
- **Unity XR** (XR Interaction Toolkit + XR Plugin Management over OpenXR) and **Unreal** (built-in OpenXR + VR templates) are the dominant engines.
- **WebXR**: VR/AR in the browser (`navigator.xr.requestSession('immersive-vr'/'immersive-ar')`), rendered via WebGL/WebGPU (Three.js/Babylon.js helpers). No install; capability varies by browser/device.
- **ARKit** (iOS), **ARCore** (Android) for phone AR. **Quest** (Meta) standalone Android-based; **visionOS** (Apple Vision Pro) uses RealityKit/SwiftUI + ARKit, gaze+pinch input, spatial windows.

## Spatial UI
- Put UI on **world-space canvases** at a comfortable distance (~1.5–2m) and size, curved toward the user; screen-space overlay UI does NOT work in stereo VR (no single screen). In Unity: `Canvas` render mode = World Space.
- Text must be large and high-contrast; keep interactive targets big (hand/controller precision is coarse). Keep UI within a comfortable FOV cone; avoid forcing large head/eye movement. Diegetic UI (on objects/wrist) feels natural.

## Gotchas -> Fix
- **Frame drops cause nausea, not just stutter** -> hold the device's native Hz relentlessly; profile GPU/CPU per-eye, cut overdraw/draw calls, use single-pass stereo, fixed foveation, baked lighting. Reprojection is a fallback, not a budget.
- **Wrong world scale (everything feels giant/tiny)** -> VR is 1:1 with reality; 1 unit = 1 meter. Model and import at real-world scale or presence breaks and locomotion feels off. Verify against a 1.7m avatar.
- **Smooth locomotion makes players sick** -> default to teleport; if offering smooth movement, add vignette/tunneling, snap-turn, low acceleration, constant velocity, and let users toggle comfort options.
- **Tracking loss (dark room, fast motion, occluded controllers)** -> handle gracefully: freeze/fade content, show a message, don't teleport the player when pose is lost; provide a recenter/reset-view action.
- **Screen-space / overlay UI invisible or double-imaged in VR** -> use World Space canvases at a set distance; never screen-space overlay. Reticles/HUD must be placed in 3D at a comfortable depth to avoid eye strain.
- **Camera moved by the game → instant sickness** -> never take control of the camera the user didn't drive (no cutscene camera moves, head-bob, forced FOV, or knockback that rotates the view). Move the world/vehicle around a stable head.
- **AR holograms float in front of real objects** -> enable depth/occlusion (LiDAR or depth API); without it virtual content always draws on top and looks fake.
- **AR anchor drifts / content slides** -> rely on anchors (not raw world coordinates) and let SLAM refine; expect drift over distance/time; re-localize with cloud/shared anchors for persistence and multiplayer.
- **UI text unreadable / targets missed** -> increase text size and contrast, enlarge hit targets, place UI within the comfortable FOV; account for coarse hand-tracking precision.
- **Built for one headset only** -> target **OpenXR** (and Unity XR Interaction Toolkit) instead of a vendor SDK to avoid rewrites across Quest/SteamVR/Vision Pro.
- **Eye/depth buffer or vergence mismatch causes eye strain** -> keep focal content at comfortable depth (~1–3m), avoid objects too close to the face, match convergence to placement; don't put fixed UI at the near clip.
- **Hand tracking unreliable in bad lighting** -> always offer controller fallback; design large, forgiving pinch/poke targets; don't gate core actions on precise finger poses.
