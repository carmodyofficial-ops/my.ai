# React Native + Expo

## Setup & Expo
- Prefer **Expo** (managed) for most apps: `npx create-expo-app`, `npx expo start`, Expo Go for quick preview. `expo-*` modules (camera, location, notifications, secure-store, image) cover most native needs — no Xcode/Android Studio for JS-only changes.
- Need custom native code / a module not in Expo? Use **Expo prebuild** + **development builds** (`npx expo run:ios`/`run:android`, or EAS Build) — you keep `app.json`/config plugins, not a raw `ios/`/`android/` you hand-edit. "Bare" workflow only if you must fully own native projects.
- Config in `app.json`/`app.config.js`; native tweaks via **config plugins**, not manual edits (prebuild regenerates native dirs).
- New apps default to React Native's **New Architecture** (Fabric + TurboModules + JSI, bridgeless). Old bridge is being removed.

## Components & styling
- Core: `View` (div), `Text` (all text MUST be inside `<Text>`), `Image`, `ScrollView` (small content), `Pressable` (preferred touch), `TextInput`, `FlatList`/`SectionList`. No HTML elements.
- Styling = JS objects, subset of CSS: `StyleSheet.create({ box: { flex: 1 } })`. Units are density-independent (no `px`/`%` strings except a few). No cascade/inheritance (except some `Text` props). No CSS grid.
- Layout is **Flexbox**, default `flexDirection: 'column'` (differs from web's `row`). `flex: 1` to fill, `justifyContent` (main axis), `alignItems` (cross axis). `position: 'absolute'` relative to parent.
- Platform styling: `Platform.OS === 'ios'`, `Platform.select({ ios, android })`, `.ios.tsx`/`.android.tsx` file extensions. `useWindowDimensions()` for responsive; `SafeAreaView`/`react-native-safe-area-context` for notches.

## Navigation
- **React Navigation** (`@react-navigation/native`) is standard, or **Expo Router** (file-based, built on it).
- Navigators: `createNativeStackNavigator` (native push/animations), `createBottomTabNavigator`, `createDrawerNavigator`. Wrap app in `NavigationContainer`.
- `navigation.navigate('Details', { id })`, `.push`, `.goBack`, `.setParams`; read `route.params`. `useNavigation()`/`useRoute()` hooks. Deep linking via `linking` config.
- Expo Router: files in `app/` are routes (`app/index.tsx`, `app/[id].tsx`), `<Link href>`, `useRouter()`, `_layout.tsx` for stacks/tabs.

## State & data
- Local: `useState`/`useReducer`. Server state: **TanStack Query** (`useQuery`/`useMutation`) — caching, retries, background refetch. Global: Zustand/Redux Toolkit/Context.
- Fetch with `fetch`/`axios`. Persist with `AsyncStorage` (`@react-native-async-storage`) for non-sensitive, `expo-secure-store`/Keychain for tokens. `MMKV` for fast sync storage.

## Lists & performance
- `FlatList` for long lists (virtualized): `data`, `renderItem`, **`keyExtractor`** (stable id). Tune `initialNumToRender`, `windowSize`, `maxToRenderPerBatch`, `removeClippedSubviews`. Use `getItemLayout` for fixed-height rows (skips measurement).
- Memoize rows with `React.memo`; stable `renderItem`/keyExtractor (`useCallback`); avoid inline functions/objects in render.
- **FlashList** (Shopify) is a faster drop-in for heavy lists. Never nest a `FlatList` in a `ScrollView` of the same axis.

## Native modules & bridge (New Architecture)
- **Fabric** = new renderer (concurrent React, synchronous layout via JSI). **TurboModules** = lazy native modules over **JSI** (direct C++ JS↔native calls, no async JSON bridge). **Codegen** generates typed native interfaces from TS specs.
- Legacy bridge: async, serializes everything to JSON — batching many calls (per-frame, gestures) causes jank. New arch removes this via JSI.
- Author native: Expo Modules API (Swift/Kotlin) is the modern path; Turbo Native Modules for RN core. `NativeModules.X` for legacy.

## Animation & gestures
- **Reanimated**: animations run on the **UI thread** (worklets, `'worklet'`), not JS — smooth under load. `useSharedValue`, `useAnimatedStyle`, `withTiming`/`withSpring`, `useDerivedValue`. `runOnJS`/`runOnUI` to cross threads.
- **react-native-gesture-handler**: native-thread gestures (`Gesture.Pan()`, `.Tap()`, `GestureDetector`) — replaces the JS `PanResponder` (janky). Pairs with Reanimated.
- `LayoutAnimation`/`Animated` (older) run partly on JS — prefer Reanimated for 60fps.

## Debugging
- **React Native DevTools** (Hermes-based, Chrome DevTools) is the current debugger; Flipper is deprecated. Dev menu: shake / `Cmd+D`/`Cmd+M`. Fast Refresh on save.
- **Hermes** JS engine (default) — smaller, faster start, bytecode. Use its profiler for JS perf; native profilers (Xcode Instruments / Android Studio Profiler) for native.
- Errors: red box (fatal) / yellow box (LogBox warnings). Source maps for release stack traces (Sentry).

## Platform APIs & device features
- Via Expo modules: `expo-camera`, `expo-location` (foreground/background perms), `expo-notifications` (push tokens + local), `expo-image-picker`, `expo-file-system`, `expo-sensors`, `expo-haptics`, `expo-av`/`expo-video`, `expo-linking` (deep links), `expo-constants`. Community: `react-native-permissions` for granular permission flows.
- Permissions: request at point of use, handle denied/blocked (send to Settings); declare in `app.json`/Info.plist/AndroidManifest. iOS needs purpose strings (`NSCameraUsageDescription`).
- Push: FCM (Android) / APNs (iOS); Expo push service abstracts both. Background tasks limited by OS (`expo-task-manager`, `expo-background-fetch`).

## Env, config & i18n
- Env/secrets: `app.config.js` + `extra`, `expo-constants`, or `react-native-config`; never ship secrets in the JS bundle (it's shippable/inspectable). Use EAS secrets for build-time. App variants (dev/staging/prod) via config + separate bundle IDs.
- i18n: `i18next`/`react-i18next` or `expo-localization` + `i18n-js`; RTL via `I18nManager`. Accessibility: `accessible`, `accessibilityLabel`, `accessibilityRole`, `accessibilityState` on `Pressable`/`View`; test with VoiceOver/TalkBack.

## Testing
- Unit/component: **Jest** + `@testing-library/react-native` (`render`, `screen`, `fireEvent`, `userEvent`, query by role/text/testID). Mock native modules. Snapshot tests sparingly.
- E2E: **Maestro** (simple YAML flows, recommended) or **Detox** (gray-box, native). Run on device/simulator in CI. `jest --coverage`; type-check with `tsc`; lint ESLint + Prettier.

## Gotchas -> Fix
- **Bridge/JS-thread jank** on gestures/scroll (old arch): heavy JS per frame. Fix: Reanimated worklets + gesture-handler (UI thread); enable New Architecture; offload work.
- **`FlatList` jank / blank cells while scrolling**: unstable keys, non-memoized rows, variable heights. Fix: `keyExtractor` id, `React.memo` rows, `getItemLayout`, FlashList.
- **`VirtualizedList: nested inside ScrollView`** warning + broken virtualization. Fix: use `FlatList`'s `ListHeaderComponent`/`ListFooterComponent`, don't nest same-axis scrollers.
- **Text not rendering / "Text strings must be rendered within a <Text>"**: raw string outside `<Text>`. Fix: wrap it.
- **Platform diffs**: shadows (iOS `shadow*` vs Android `elevation`), keyboard avoidance (`KeyboardAvoidingView` behavior differs), status bar, back button (Android hardware back). Fix: `Platform.select`, test both OSes on device.
- **Flexbox surprise**: default `flexDirection: column` unlike web. Fix: set direction explicitly.
- **State update after unmount / stale async**: setState in a resolved fetch after navigate-away. Fix: TanStack Query, or abort/guard with a mounted ref.
- **Storing secrets in AsyncStorage** (plaintext). Fix: `expo-secure-store`/Keychain/Keystore.
- **Large images / memory**: full-res images in lists → OOM. Fix: resize/cache (`expo-image`), correct `resizeMode`, thumbnails.
- **`console.log` / dev-only slowness in release**: remove logs, always test a **release/production build** (`--variant release`, EAS build) — Hermes + minification change behavior/perf.
- **`node_modules`/native cache corruption** after upgrades: Fix: `npx expo start -c`, delete `node_modules`, `pod install`, clear Metro cache; check the Expo/RN upgrade helper.
- **New Architecture incompatible library**: some old native libs break under Fabric. Fix: check lib's new-arch support / update / find alternative before enabling.
- **Expo Go can't run custom native modules**: a lib needing native code won't work in Expo Go. Fix: create a development build (`expo-dev-client` / EAS build).
- **Version/SDK mismatch after upgrade**: JS ↔ native ↔ Expo SDK skew → red screens. Fix: use `npx expo install` (pins compatible versions), follow the RN/Expo upgrade guide, don't hand-bump.
- **Animating layout props on the JS thread** (`width`/`height`/non-transform) → jank. Fix: prefer `transform`/`opacity` in Reanimated worklets; avoid animating layout.
- **`useEffect` cleanup missing** on subscriptions/timers/listeners → leaks/duplicate handlers. Fix: return a cleanup function; remove listeners.
