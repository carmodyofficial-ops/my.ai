# Android Companion — Build & Install

Source: `apps/myai-glasses-android/`, split into two modules:

- **`:core`** (pure JVM — reducer, SSE parser, pairing payload, gateway
  client, wearables adapter interface + mock): **compiled and all 12 unit
  tests passing on the Ubuntu ARM host** (Gradle 8.9 + JDK 17, 2026-07-12).
- **`:app`** (Compose UI, Keystore, audio, Meta SDK adapter): **BUILT on the
  ARM host** (2026-07-12) — `app/build/outputs/apk/debug/app-debug.apk`
  (~25 MB, applicationId `ai.my.glasses`, v2-signed with the debug cert,
  verified with apksigner). The mock-adapter variant; the `metadat` source
  set (real Meta SDK) still needs Meta credentials and remains
  not-compiled-against-real-artifacts.

### Building on a linux-aarch64 host (the recipe used here)

Google ships no linux-aarch64 `aapt2`; everything else in the toolchain is
JVM. The fix is Google's **official x86_64 aapt2 under user-mode qemu**:

1. `~/android-tools/`: Temurin JDK 17 (aarch64), Gradle 8.9, Android
   cmdline-tools; `sdkmanager --licenses`, install `platforms;android-35`
   (+ `build-tools;34.0.0` for apksigner).
2. Fetch `aapt2-8.5.2-11315950-linux.jar` from Google's maven, unzip the
   `aapt2` binary; export a debian:stable-slim (amd64) docker image as an
   x86_64 rootfs for its dynamic libs.
3. Wrapper (must be NAMED `aapt2` — AGP checks):
   `exec qemu-x86_64-static -L <rootfs> <path>/aapt2 "$@"`
4. `~/.gradle/gradle.properties`:
   `android.aapt2FromMavenOverride=/home/youruser/android-tools/aapt2-wrap/aapt2`
5. `gradle -p apps/myai-glasses-android :app:assembleDebug`

Install on the phone: `adb install app-debug.apk` (enable USB debugging), or
copy the APK over and open it (allow install-unknown-apps).

## Two APKs (both built on this host, 2026-07-12)

| File (in `apps/myai-glasses-android/`, git-ignored) | Build | Contains |
|---|---|---|
| `myai-glasses-mock-debug.apk` | `gradle :app:assembleDebug` | mock glasses adapter, **zero** Meta SDK code — runs on any Android 12+ phone |
| `myai-glasses-metasdk-debug.apk` | `gradle :app:assembleDebug -PmetaSdk=true` | **real Meta DAT SDK v0.8** + `MetaDatAdapter`, MetaAppID baked into the manifest |

Both are v2 debug-signed (apksigner-verified). Verified by inspection: the mock
APK contains 0 `com/meta/wearable/dat` references; the metaSdk APK contains
~1339 plus `MetaDatAdapter`/`MetaGlassesHost`.

**Toolchain note:** the Meta SDK artifacts carry Kotlin 2.2 metadata and pull
in AndroidX that needs a recent AGP, so the project is pinned to the same
versions as Meta's CameraAccess sample: **Gradle 8.14.1, AGP 8.11.1, Kotlin
2.2.21, compileSdk 36**. Older combinations fail with "Module was compiled with
an incompatible version of Kotlin".

## Prerequisites

- Android Studio (Koala+) with JDK 17, Android SDK 35.
- A phone on Android 12+ (API 31 — required for the HFP mic-routing API).
- For REAL glasses (all optional for mock builds):
  1. Ray-Ban Meta glasses, firmware **V127+**; Meta AI app **V272+**.
  2. Meta AI app → Settings → App Info → tap version 5× → **Developer Mode ON**.
  3. Register the app at the **Wearables Developer Center** → `MetaAppID` +
     `ClientToken`.
  4. GitHub token with `read:packages` for the Meta Maven repo, in
     `~/.gradle/gradle.properties`:
     ```
     gpr.user=<github-username>
     gpr.token=<token>
     ```
  5. Uncomment the two `<meta-data>` entries in `AndroidManifest.xml` and add
     `meta_app_id` / `meta_client_token` string resources (keep them out of
     source control — e.g. a git-ignored `secrets.xml`).

## Build variants

```bash
# Mock build — no Meta credentials, runs on any phone/emulator:
./gradlew assembleDebug

# Real-glasses build — adds mwdat artifacts + MetaDatAdapter source set:
./gradlew assembleDebug -PmetaSdk=true

# JVM unit tests (reducer, SSE parser, pairing payload):
./gradlew testDebugUnitTest
```

`MetaDatAdapter` is now **fully implemented against the real SDK** (no TODOs):
`Wearables.initialize` → `startRegistration` (Meta AI app bounce, returns via
the `myai-glasses://` scheme) → `checkPermissionStatus`/`RequestPermissionContract`
for the glasses CAMERA permission → `createSession(AutoDeviceSelector)` →
`addStream(LOW/7fps)` → `capturePhoto()` → downscale+JPEG → stop stream.
It compiles against mwdat 0.8.0 but has **not run on physical glasses**.

## First run (mock mode, validates the whole local pipeline)

1. Host: make the gateway reachable from the phone —
   `APP_BIND=<LAN-IP>`, `MYAI_WEARABLES_ADVERTISE_HOST=<LAN-IP>`, restart
   the odysseus service (OPERATIONS_RUNBOOK.md; TLS strongly recommended).
2. Desktop (admin): `POST /api/wearables/v1/pairings` → QR/payload.
3. App → "Pair with your my.ai host" → paste/scan payload → paired.
4. Type a question → streamed answer from your local model.
5. "Look & Ask" in mock mode sends a synthetic JPEG — expect a confused but
   *local* model answer; with real glasses it sends the actual capture.

## Permissions the app asks for

`INTERNET` (gateway), `RECORD_AUDIO` + `BLUETOOTH_CONNECT` +
`MODIFY_AUDIO_SETTINGS` (voice turns), `CAMERA` (QR scan only — glasses
imagery comes via the Meta SDK, not the phone camera), foreground-service
mic type (long voice sessions with the screen off).

**Only `BLUETOOTH_CONNECT` gates the glasses.** The app requests the whole set
at launch, but just that one decides whether the DAT SDK is initialized —
matching Meta's own samples, which ask for Bluetooth/Bluetooth-Connect/Internet
and nothing else. Denying the phone camera or the mic costs you QR scanning and
voice, never the glasses.

## Connecting the glasses

Registration with the Meta AI app is a **user action**, on a button
("Connect glasses", setup step 1 and the home status card) — not something that
only happens once at process start. Tap it again after fixing anything below;
pull-to-refresh runs the same sequence when the app isn't registered yet.

    register (bounce through Meta AI) → glasses CAMERA permission → device session

When it doesn't work, the status line names the stage it stopped at
(`SDK not started` / `Meta AI app unavailable` / `not registered` /
`not connected`), and the red hint under it names the fix. For anything less
obvious, **Diagnostics** (nav drawer → Diagnostics → Refresh) prints the SDK's
own account: companion-app version, Developer Mode, registration state, how many
devices the SDK can see, the active device's link state and firmware
compatibility, and the last registration/session error. Start there.

Prerequisites that produce a *specific* message when missing: Meta AI app
installed (`META_AI_NOT_INSTALLED`), Developer Mode on + app registered in the
Wearables Developer Center (`META_DEVELOPER_MODE_REQUIRED` /
`REGISTRATION_FAILED`), glasses firmware new enough (`GLASSES_UPDATE_REQUIRED`),
Nearby-devices permission (`BLUETOOTH_PERMISSION_DENIED`).
