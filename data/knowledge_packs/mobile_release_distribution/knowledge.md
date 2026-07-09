# Mobile Release & Distribution

## iOS code signing
- Every build is signed with a **certificate** (Apple Development / Apple Distribution) + a **provisioning profile** (ties App ID + certificate + devices + entitlements). Managed by a **team** in Apple Developer Program ($99/yr).
- App identity: **Bundle ID** (`com.company.app`) + explicit App ID with entitlements (push, App Groups, iCloud). **Capabilities** toggled in Xcode add entitlements + provisioning.
- Automatic signing (Xcode manages profiles) is simplest; manual signing for CI/reproducibility. **Fastlane match** stores certs/profiles in a shared encrypted git repo so a team/CI share one identity (avoids "revoke storm").
- Distribution types: **App Store**, **Ad Hoc** (registered devices), **Enterprise** (in-house, separate program), **Development**. Archive → export `.ipa` with matching profile.

## Android signing
- **Upload key** (your keystore, `.jks`) signs the app you upload; **Google Play App Signing** re-signs with the **app signing key** Google holds — enroll once, Play manages the final key. Losing the upload key is recoverable (contact Google); losing a legacy self-managed key is fatal.
- Keystore: `keytool -genkey -v -keystore upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`. Guard it + password (never in git; use secrets/env in CI). Configure `signingConfigs` in `build.gradle`.
- Ship **Android App Bundle (`.aab`)** to Play (Play generates per-device APKs); `.apk` only for direct/sideload. `applicationId` = package identity (immutable after publish).

## Versioning
- iOS: `CFBundleShortVersionString` (marketing, e.g. `1.4.0`, user-visible) + `CFBundleVersion` (build number, must strictly increase per upload to a given version).
- Android: `versionName` (user-facing string) + `versionCode` (monotonically increasing integer — Play rejects ≤ previous).
- Use **semver** for marketing version; auto-bump build/versionCode in CI (git count/timestamp). Tag releases; keep a changelog / release notes.

## Store submission & review
- **App Store Connect**: create app record, upload build (Xcode/Transporter/Fastlane), fill metadata (name, subtitle, description, keywords, screenshots per device size, privacy policy URL), **App Privacy** questionnaire (data collection "nutrition label") + **Privacy Manifest** (`PrivacyInfo.xcprivacy`, required APIs & tracking domains), age rating, export compliance. Submit for **App Review** (typically ~24–48h). Human review — can reject.
- **Google Play Console**: create app, upload `.aab`, store listing, content rating questionnaire, **Data safety** form, target API level requirement (Play enforces recent `targetSdkVersion`), app access/declarations (permissions, foreground service, ads). Review now takes hours–days (longer for new accounts).
- New Apple/Google developer accounts and apps face stricter, slower review.

## Testing tracks
- iOS **TestFlight**: internal testers (up to 100, no review) get builds fast; external testers (up to 10,000, needs a lightweight Beta App Review) via public/email links. Builds expire after 90 days.
- Play testing tracks: **internal** (fast, up to 100 testers), **closed** (alpha/beta, opt-in lists/groups), **open** (public beta), then **production**. New personal accounts must run a closed test (e.g. 12+ testers, ~14 days) before production access.
- Promote a build up the tracks; keep the same signing.

## CI/CD
- **Fastlane**: cross-platform lanes — `match` (signing), `gym`/`build_app` (iOS build), `gradle` (Android), `pilot` (TestFlight), `supply` (Play), `deliver` (metadata/screenshots), `snapshot` (screenshots). Scriptable `Fastfile`.
- **EAS** (Expo Application Services): `eas build` (cloud iOS/Android builds, no local Xcode), `eas submit` (to stores), `eas update` (OTA). Config in `eas.json`; handles credentials.
- **Codemagic / Bitrise / GitHub Actions / Xcode Cloud**: hosted mac + linux runners, signing secrets, build → test → sign → distribute. Store certs/keystores as encrypted secrets, never in repo.
- Pipeline: lint/test → build signed artifact → upload to TestFlight/internal track → (gate) → promote to production with staged rollout.

## OTA updates & limits
- **Expo Updates / EAS Update** and **CodePush** push **JS bundle + assets** over the air — instant fixes without a store review. **Only JS/asset changes**; any native code change (new native module, SDK/runtime version, permissions, config plugin) requires a new store build. Match update to the correct **runtime version**/binary or it won't apply.
- **Store policy**: OTA is allowed for bug fixes/content, but must not materially change the app's purpose or bypass review for significant features — abuse risks rejection. Roll updates gradually and support rollback to a prior bundle.

## Staged rollout, crash reporting, analytics
- **Staged/phased rollout**: Play percentage rollout (1→5→10→…→100%), Apple phased release (7-day auto ramp). Halt/rollback on a crash-rate spike. Watch first hours closely.
- **Crash reporting**: Firebase Crashlytics / Sentry / App Store & Play vitals. Upload **dSYMs (iOS)** / **ProGuard/R8 mapping files (Android)** so stack traces symbolicate/deobfuscate — automate in CI or crashes are unreadable. Track crash-free-users %.
- **Analytics**: Firebase/Amplitude/etc.; respect App Tracking Transparency (`ATTrackingManager` prompt on iOS for IDFA) and consent; declare data collection in App Privacy/Data safety.
- **ASO** (store optimization): title + subtitle/short description + keywords, compelling screenshots/preview video, localized listings, ratings prompts (`SKStoreReviewController`/In-App Review API), respond to reviews, A/B test store listing.

## Common rejection reasons -> Fix
- **Crashes / broken build / placeholder content** on review. Fix: test the exact release build on device; no lorem/debug.
- **Privacy: missing policy URL, wrong App Privacy/Data safety answers, missing iOS Privacy Manifest / undeclared tracking**. Fix: complete & accurate privacy declarations + `PrivacyInfo.xcprivacy`.
- **Missing purpose strings** for permissions (iOS `NSCameraUsageDescription` etc.) → crash/reject. Fix: add clear `Info.plist` usage descriptions; request only what you use.
- **Apple 4.3 "spam/duplicate"** or thin/low-value app. Fix: distinct value, quality UX.
- **Apple 3.1.1 payments**: using external payment for digital goods instead of In-App Purchase. Fix: use IAP for digital content (physical goods/real-world services use external).
- **Sign in with Apple required** when offering third-party social login (iOS). Fix: add it.
- **Android target API too low / disallowed permissions / foreground-service without declared type / background location without justification**. Fix: raise `targetSdkVersion`, remove unused permissions, declare service types, justify sensitive perms.
- **Incomplete metadata / bad screenshots / broken demo account or login**. Fix: provide working test credentials in review notes; accurate screenshots.
- **Lost/mismatched signing** (wrong provisioning, revoked cert, wrong keystore) → upload fails. Fix: `match`/managed signing, keep keystore + passwords in secrets, enroll in Play App Signing.
- **versionCode/build number not incremented** → "already exists". Fix: auto-increment in CI.
- **OTA update not applying**: runtime/binary mismatch. Fix: align runtime version; ship a native build when native changed.
- **Unsymbolicated crashes** (raw addresses, obfuscated names). Fix: upload dSYMs / R8 mapping per release; automate in CI; retain per build.
- **Export compliance / encryption declaration** stalls the build. Fix: set `ITSAppUsesNonExemptEncryption` in Info.plist (usually `false` for standard HTTPS).
- **Guideline 5.1.1 / permission over-ask**: requesting data/permissions without clear need or up-front. Fix: request in context, justify, minimize scope.
- **Screenshots/metadata reference other platforms or unavailable features**. Fix: platform-accurate, current-build screenshots; no "coming soon".

## Release checklist
- Bump version + build/versionCode; update release notes/changelog; freeze the release branch.
- Build **signed release** artifact (`.ipa` / `.aab`) via CI; run full test suite + lint on it.
- Verify privacy declarations (App Privacy / Data safety / Privacy Manifest), permission strings, deep links, push, and third-party keys for prod.
- Upload dSYM / mapping to crash reporter; confirm analytics/consent gating.
- Ship to TestFlight/internal track → smoke test on real devices (both OSes, min + latest OS) → promote with **staged rollout** → monitor crash-free % and reviews → halt/rollback on regression.
