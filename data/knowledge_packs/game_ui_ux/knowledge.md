# Game UI/UX
## HUD Design
- Show only what the player needs now; push secondary info to menus. Group by priority: health/ammo (constant), objectives (contextual), buffs (transient).
- Position by importance and eye path: corners for persistent stats, center-adjacent for critical alerts (low health flash). Keep the center clear for gameplay.
- Fade/hide HUD elements when irrelevant (contextual HUD) to reduce clutter; animate in on state change (damage vignette, ammo on reload).
- Diegetic HUD lives in the world (gun ammo counter, Dead Space health spine) -> immersion; non-diegetic overlays the screen -> clarity. Spatial (in 3D world, not fiction) and meta (screen-space fiction, e.g. blood splatter) are the other two of the four UI classes.
## Menu Navigation
- Support every input scheme the platform allows: mouse (free cursor), keyboard, gamepad (focus + D-pad/stick), touch. Design for the most constrained (gamepad focus) first.
- Gamepad/keyboard need an explicit focus/selection system: one highlighted element, directional navigation between them, A/Enter = confirm, B/Esc = back (consistent everywhere).
- Set a default focused element on menu open so controller users can act immediately; wrap or clamp navigation at edges (choose one, be consistent).
- Touch: min tap target ~44-48px (9mm); space targets to avoid mis-taps; thumb-reachable zones on phones. Avoid hover-only affordances.
## Input Feedback & Game Feel
- Every input needs immediate feedback (<100ms): button press animates/sounds even before the action resolves. Missing feedback reads as "unresponsive".
- Juice: hover/press states, scale/color tween, click SFX, haptics/rumble, screen shake for impact. Confirm destructive actions but keep frequent ones frictionless.
- Telegraph state changes: animate transitions (slide/fade) so players track what changed; instant snaps disorient.
## Readability
- Contrast: text must pass over any background — use outlines, drop shadows, or semi-opaque backing panels; don't rely on color alone. Target WCAG-ish contrast for body text.
- Text scaling: support UI scale / font size options; never hardcode tiny fonts. Test at min supported resolution and on a TV at couch distance (10-foot UI).
- Title-safe / action-safe zones: keep critical UI within ~90%/95% of screen (TV overscan, notches, rounded corners). Anchor to safe area, not screen edge.
- Icon + text label beats icon alone for clarity; consistent iconography across the game.
## UI Performance
- Unity uGUI: any change to a Canvas rebuilds its whole batch (layout + mesh). Fix: split static and dynamic elements onto separate Canvases so frequent updates don't rebuild everything.
- Avoid per-frame layout groups and `Text` updates that trigger rebuilds; disable `Raycast Target` on non-interactive graphics to cut input raycast cost.
- Overdraw from many stacked transparent UI layers is costly on mobile; flatten, reduce full-screen overlays. Pool/reuse list items instead of instantiating (recycler pattern) for scroll lists.
- Godot: Control nodes + anchors; avoid heavy `_process` UI updates, update on signal instead. Web/DOM UI: batch DOM writes, avoid layout thrash.
## Information Architecture & Flow
- Keep menu depth shallow (rule of thumb: goal reachable in <=3 clicks/steps); breadcrumb the current location in deep trees. Group related settings under labeled tabs/sections.
- Consistent back-out: B/Esc always steps up one level and never loses unsaved-safe state unexpectedly; confirm before discarding edits.
- Modal vs non-modal: use modals sparingly for blocking decisions; avoid stacking modals. Pause-menu should pause single-player.
- Progressive disclosure: show basics first, advanced options behind an "Advanced" toggle to avoid overwhelming new players.
## Onboarding & Prompts
- Teach controls contextually (just-in-time prompts) over a wall of tutorial text; fade the prompt once the player performs the action.
- Show input glyphs for the active device and update live on device switch; label with verb ("[A] Jump"), not just the glyph.
- Tooltips on hover/focus for dense HUD/inventory; keep them short, positioned to not cover the thing they describe.
## Accessibility
- Remappable controls (full rebinding, including for accessibility devices); don't hardcode input prompts — show the active device's glyphs.
- Subtitles: on by default option, readable size, speaker names, backing panel; separate sliders for dialogue vs SFX/music volume; closed captions for important non-speech audio.
- Colorblind modes (protanopia/deuteranopia/tritanopia): never encode critical info by color alone — add shape/icon/pattern/text. Provide palette options.
- Options: difficulty separate from accessibility, camera-shake toggle, motion-reduction, hold-vs-toggle for actions, aim assist, adjustable timing windows.
## Gotchas -> Fix
- **Controller can't navigate menu / nothing highlighted**: no focus system or no default selection. Fix: set an explicitly-focused element on open, wire directional navigation, restore focus after closing sub-panels.
- **Unity UI tanks framerate**: whole Canvas rebuilding on every small change. Fix: separate dynamic elements to their own Canvas, disable unnecessary Raycast Targets, avoid per-frame layout.
- **Text unreadable over bright/busy backgrounds**: relying on the text color alone. Fix: add outline/shadow or a semi-opaque backing, increase contrast.
- **UI clipped on TV / behind notch**: elements pinned to screen edge. Fix: anchor to title-safe area (~5% inset), respect device safe-area insets.
- **Buttons feel dead/unresponsive**: no immediate press feedback. Fix: add press animation + SFX on input event, not on action completion (<100ms feedback).
- **Touch targets hard to hit**: too small or too close. Fix: 44px+ targets, add spacing/padding, enlarge hit area beyond the visual.
- **Mouse works but gamepad focus jumps randomly**: navigation graph not defined. Fix: set explicit up/down/left/right navigation or use a well-formed automatic layout.
- **Colorblind players can't tell states apart** (red/green ammo, team colors): color-only encoding. Fix: add icons/shapes/labels, offer colorblind palettes.
- **Prompts show wrong buttons** (keyboard glyphs on gamepad): hardcoded prompts. Fix: detect active input device and swap glyph set live.
- **Scroll list stutters with many items**: instantiating every row. Fix: recycle/pool visible items (virtualized list).
- **Menu transitions feel jarring**: instant show/hide. Fix: animate fade/slide over ~150-250ms so players track the change.
- **Players buried in menus / can't find a setting**: too-deep tree, no grouping. Fix: flatten to <=3 levels, add tabs/search, breadcrumb location.
- **Stacked modals trap the player**: modal-on-modal. Fix: one modal at a time, always-reachable back/cancel.
- **Tutorial dumps too much text**: front-loaded wall of instructions. Fix: contextual just-in-time prompts, teach one action at a time, fade after use.
- **Tooltip covers the item it explains**: fixed position. Fix: flip tooltip to available space, offset from cursor/focus.
- **Motion/shake makes players sick**: no toggle. Fix: add camera-shake and motion-reduction options, reduce default intensity.
