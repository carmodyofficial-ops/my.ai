# Roblox UI Advanced (responsive, frameworks, perf)

## Responsive UI: scale vs offset
- `UDim2 = {Scale, Offset}` per axis. **Scale** = fraction of parent (resolution-independent, use for layout/positioning). **Offset** = absolute pixels (use sparingly — borders, fixed icons; breaks across devices).
- Rule: size/position with **Scale** for anything that must adapt; reserve Offset for pixel-exact chrome. Pure-offset UI looks tiny on phones / huge on 4K.
- **AnchorPoint** (0..1) sets the element's own pivot; `AnchorPoint = Vector2.new(0.5, 0.5)` + `Position = UDim2.fromScale(0.5, 0.5)` = true centering regardless of size. Without AnchorPoint, Position is the top-left corner.
- **UIScale** (a `UIScale` instance with `.Scale`) multiplies an entire subtree — the pro way to scale a whole menu to viewport. Drive it from a reference resolution:
```lua
local BASE = Vector2.new(1280, 720)
local function fit()
    local vp = workspace.CurrentCamera.ViewportSize
    uiScale.Scale = math.min(vp.X / BASE.X, vp.Y / BASE.Y)
end
workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(fit); fit()
```
- **AutomaticSize** (`Enum.AutomaticSize.X/Y/XY`) grows a frame to fit children/text — set the *cross* axis with Scale/Offset and let the other auto-size. Pair with `UIListLayout` for dynamic lists, and with `TextLabel.TextWrapped` for growing text bubbles.
- **Safe insets**: `GuiService:GetGuiInset()` returns top-bar inset (Vector2). On phones with notches, `ScreenGui.ScreenInsets = Enum.ScreenInsets.DeviceSafeInsets` (or `CoreUISafeInsets`) keeps UI out of the notch/home indicator. Anchor critical buttons inside safe area.
- `ScreenGui.IgnoreGuiInset = true` extends UI under the topbar (full-bleed backgrounds); keep interactables below the inset anyway.

## Layout constraints
- **UIListLayout**: auto-arranges children in `FillDirection` (Vertical/Horizontal) with `Padding` (UDim), `HorizontalAlignment`/`VerticalAlignment`, and `SortOrder` (`LayoutOrder` int, else name). Children need no manual Position. `Wraps = true` (newer) wraps.
- **UIGridLayout**: `CellSize` (UDim2 — mix scale+offset), `CellPadding`, `FillDirectionMaxCells`, `StartCorner`. `CellSize` with Scale makes responsive grids.
- **UIPageLayout**: swipeable pages (`:Next()`/`:Previous()`/`:JumpTo()`), `Circular`, `Animated`, `TweenTime`. Good for carousels/tutorials.
- **UITableLayout**: rows/cols with `FillEmptySpaceColumns`.
- **UIAspectRatioConstraint**: locks `AspectRatio` (W/H); `DominantAxis` + `AspectType` (`FitWithinMaxSize`/`ScaleWithParentSize`) — the trick for square icons / 16:9 panels that stay proportional on any screen. Combine with Scale sizing.
- **UISizeConstraint** (min/max pixel size), **UITextSizeConstraint** (clamp TextSize with `TextScaled`), **UIPadding** (inner inset), **UICorner** (rounded), **UIStroke** (borders/outlines, `ApplyStrokeMode`).
- Order matters: a frame with `UIAspectRatioConstraint` + `UIListLayout` — the aspect ratio governs the frame, the list governs children.

## Modern frameworks
### Fusion (reactive state)
- `Value`, `Computed`, `Observer`, `Spring`, `Tween`. UI is a function of state; changing a `Value` re-evaluates dependent `Computed`s and updates only affected props.
```lua
local count = Value(0)
local label = New "TextLabel" {
    Text = Computed(function() return "Score: " .. count:get() end),
    Size = UDim2.fromScale(1, 0.1),
}
count:set(count:get() + 1)  -- label.Text updates automatically
```
- `Spring(goalState, speed, damping)` = physics-based motion bound to state (smooth, interruptible). `Children` / `[Children]` for nesting; `[OnEvent "Activated"] = fn` for events; `[Cleanup]` for teardown. Fusion 0.3 renamed some APIs (scoped `scope:Value(...)`) — check version.
### Roact / React-lua (declarative components)
- Components return element trees; a **virtual tree diffs against the previous** (reconciliation) and mutates only changed Instances. `Roact.createElement`, `Roact.mount`, `Roact.update`, `Roact.unmount`.
- State: class components `setState` / hooks (react-lua: `useState`, `useEffect`, `useMemo`, `useCallback`, `useRef`, `useContext`). Only changed subtrees re-render.
- **Keys** on list children (`[Roact.createElement(...)]` in a keyed table) so the reconciler tracks identity across reorders — missing keys cause remount churn/lost state.
- react-lua (official React port) enables real hooks + concurrent patterns; Roact is the older stable API.

## Component patterns & reuse
- Author reusable components as functions: `local function Button(props) return New "TextButton" {...} end`. Parameterize via props (text, callback, theme). One source of truth for a widget type.
- Theme via a shared table / context (React) or a Fusion `Value` for palette; components read it so a theme swap re-renders all. Avoid hardcoding colors per widget.
- Data-drive lists: map an array of data → array of components; keep item components pure (props in, UI out).

## Tweening & springs
- **TweenService**: `:Create(inst, TweenInfo.new(time, Enum.EasingStyle.Quad, Enum.EasingDirection.Out, repeatCount, reverses, delayTime), {Props})` → `:Play()`. Cache/reuse `TweenInfo`. `tween.Completed:Wait()` to sequence. Cancel with `:Cancel()`.
- Tween any numeric/UDim2/Color3/Vector2 prop. `Position`, `Size`, `BackgroundTransparency`, `TextTransparency`, `Rotation`, `GroupTransparency` (CanvasGroup).
- **Springs** (Fusion `Spring`, or Flipper/custom) beat tweens for interruptible/organic motion (drag-release, hover) — retarget goal without restarting; tweens restart abruptly. Springs use speed+damping, not fixed duration.

## Input across devices
- **Selection / gamepad**: `GuiService.SelectedObject` = focused element; set `GuiObject.Selectable = true` and wire `NextSelectionUp/Down/Left/Right` (or let auto-selection work) for D-pad navigation. `GuiButton.SelectionImageObject` styles the highlight.
- **Touch vs mouse vs gamepad**: prefer `GuiButton.Activated` (fires for click, tap, AND gamepad A / Enter) over `MouseButton1Click` (mouse only). `UserInputService.TouchEnabled`/`GamepadEnabled`/`KeyboardEnabled` to detect device and adapt layout/prompts.
- `GuiService:GetGuiInset()`, `:IsTenFootInterface()` (console/TV) to enlarge UI. `ContextActionService:BindAction` with a `createTouchButton` flag makes on-screen mobile buttons automatically.
- Don't assume a cursor: mobile has no hover; provide tap targets ≥ ~44px and gamepad selection paths.

## Performance
- **Every visible GuiObject costs**; offscreen ones still render/replicate. Set `Visible = false` (or move out) on hidden panels — but toggling Visible re-lays-out. For big scroll content use **CanvasGroup** to batch a subtree into one render surface + tween `GroupTransparency` cheaply.
- **ScrollingFrame**: cap `CanvasSize`; recycle item frames (virtualize — only instantiate visible rows, reposition on scroll) for lists of hundreds+, else you spawn thousands of Instances.
- Minimize updates: don't set UI props every frame — only on state change (this is exactly what Fusion/React reconciliation buy you). Batch text updates; avoid per-Heartbeat `Text =` writes.
- `AutomaticSize` + deep `UIListLayout` nesting triggers layout recalcs — expensive on large trees; flatten where possible. Avoid thousands of individual UIStroke/UICorner (each is an instance).
- Prefer one `ScreenGui` per logical layer; excessive ScreenGuis add overhead. `ResetOnSpawn = false` to persist HUDs across respawns.

## Rich text & localization
- **RichText**: `TextLabel.RichText = true` enables `<b>`, `<i>`, `<font color="#ff0000" size="24">`, `<stroke>`, `<uc>/<sc>` tags. Escape user text (`&lt; &gt; &amp; &quot;`) before injecting or tags break / inject.
- **Localization**: `LocalizationService` + a LocalizationTable; auto-translation via `AutoLocalize` (set on GuiBase). `Translator:FormatByKey(key, args)` for parameterized strings. Design for text expansion (German ~30% longer) — use AutoSize/wrapping, never fixed-width text boxes.
- `TextScaled = true` + `UITextSizeConstraint` to fit variable-length localized text without overflow.

## Gotchas -> Fix
- **UI tiny on phone / huge on 4K** → built with Offset. Fix: Scale-based UDim2 + a `UIScale` driven by ViewportSize ratio.
- **Element off-center when it resizes** → Position is top-left corner. Fix: `AnchorPoint = (0.5,0.5)` + `Position = fromScale(0.5,0.5)`.
- **Buttons under the notch / topbar** → ignored safe insets. Fix: `ScreenInsets = DeviceSafeInsets`; check `GetGuiInset`; keep interactables in safe area.
- **Gamepad/mobile can't press button** → used `MouseButton1Click`. Fix: `Activated` (covers mouse/touch/gamepad); set `Selectable` + selection links for D-pad.
- **List items overlap / manual positions fight layout** → both manual Position and a `UIListLayout`. Fix: let the layout own positions; use `LayoutOrder`, remove manual Position.
- **Squished icons on odd aspect ratios** → no ratio lock. Fix: `UIAspectRatioConstraint`.
- **Frame spikes with big scrolling list** → thousands of Instances rendered. Fix: virtualize (recycle visible rows), cap CanvasSize, CanvasGroup for batching.
- **UI stutters** → props set every Heartbeat. Fix: update only on state change; Fusion/React reconciliation; batch.
- **RichText breaks on user input** → unescaped `<`/`&`. Fix: escape to entities before setting `Text`.
- **Localized text overflows** → fixed-size boxes, no expansion room. Fix: AutomaticSize/wrap/TextScaled + UITextSizeConstraint; plan for +30% length.
- **List loses scroll/state on reorder (Roact)** → missing keys. Fix: stable keys on list children.
- **Tween "snaps"/restarts on rapid input** → tweens can't retarget mid-flight. Fix: springs (Fusion/Flipper) with a new goal.
- **HUD disappears on respawn** → default `ResetOnSpawn = true`. Fix: set `false` on the ScreenGui.
- **Offscreen UI still costs** → left mounted/visible. Fix: unmount or Visible=false hidden layers; CanvasGroup to collapse cost.
