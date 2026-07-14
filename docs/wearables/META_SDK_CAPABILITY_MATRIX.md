# Meta Wearables Device Access Toolkit — Capability Matrix

Researched 2026-07-12 from official sources only (wearables.developer.meta.com,
developers.meta.com blog/FAQ, facebook/meta-wearables-dat-android and -ios).
Current SDK: **v0.8.0** (2026-06-25). Claims tagged **[DOC]** (documented) or
**[INF]** (inference).

## 1. Release status & distribution

- **Developer Preview** (since 2025-09; still preview as of v0.8). You can
  build and test but **cannot distribute to end users**; publishing is limited
  to select partners, expected to broaden "in 2026". **[DOC]**
- Access: SDK is public (GitHub Packages / Swift Package); register the app in
  the **Wearables Developer Center** for a `MetaAppID` + `ClientToken`. **[DOC]**
- Tester distribution via invite-only **release channels**; general release
  requires Integration Review. **[DOC]**

## 2. Devices & firmware (DAT 0.8)

Ray-Ban Meta **Gen 1 & Gen 2** (our Wayfarers), Oakley Meta HSTN/Vanguard,
Meta Ray-Ban Display. Required glasses firmware for DAT 0.8: **V127**;
Meta AI app **V272**; Developer Mode ON. **[DOC]**

## 3. Platforms & artifacts

- iOS 15.2+ / Android 10+ (**Android 12 / API 31+ needed for the
  `setCommunicationDevice` HFP mic routing we use**). **[DOC]**
- Android: `com.meta.wearable:mwdat-{core,camera,display,mockdevice}` from
  `https://maven.pkg.github.com/facebook/meta-wearables-dat-android` (needs a
  GitHub token with `read:packages`). Manifest meta-data:
  `com.meta.wearable.mwdat.APPLICATION_ID`, `…CLIENT_TOKEN`; callback
  intent-filter with a custom scheme. **[DOC]**
- iOS: Swift Package `facebook/meta-wearables-dat-ios`
  (`MWDATCore/Camera/Display/MockDevice`). **[DOC]**

## 4. Capabilities relevant to my.ai Glasses

| Capability | Verdict | Notes |
|---|---|---|
| Camera video stream | ✅ up to 720p@30 over BT Classic; WiFi transport since 0.8 | `StreamConfiguration(videoQuality, frameRate)` **[DOC]** |
| Photo capture | ✅ but **only during an active stream** (`stream.capturePhoto()`, ~1440×1080) | **[DOC]** |
| Microphone | ✅ via **standard Bluetooth HFP (8 kHz mono)** — not an SDK API; use OS audio (`AudioManager` + `TYPE_BLUETOOTH_SCO`) | beamformed wearer isolation **[DOC]** |
| Speaker / TTS out | ✅ via **A2DP** (44.1/48 kHz) — normal OS audio routing; docs explicitly list TTS | **[DOC]** |
| Battery/device state | ✅ `DeviceState` (battery, hinge, thermal) + typed session errors | **[DOC]** |
| Touch/gesture events | ❌ on camera-only glasses (no touchpad API); Display glasses get rendered-Button taps | **[DOC]** |
| Wake word / "Hey Meta" | ❌ not available to third parties; "voice invocation" on Meta's roadmap, unshipped | **[DOC]** |
| IMU / GPS | ❌ not in DAT (Web-Apps-for-Display only) | **[DOC]** |
| Background use | ✅ officially supported (published background/lock-screen guide; iOS `UIBackgroundModes`: bluetooth-peripheral, external-accessory) | **[DOC]** |
| Mock Device Kit | ✅ simulates pairing, camera (file/phone-camera/static), photo, permissions, device state, captouch; **no audio simulation** | **[DOC]** |

## 5. Hard consequences for our design

1. **No glasses-side trigger** for a third-party app on Wayfarers → v1
   activation is **push-to-talk in the app** (or phone-side VAD on an open
   HFP link as an experimental later mode). We never claim a glasses gesture.
2. **HFP/A2DP mutual exclusivity**: while the mic is open, ALL glasses audio
   drops to 8 kHz mono. The voice loop therefore: open HFP → listen → close →
   speak TTS over A2DP (or accept call-quality TTS during barge-in windows).
3. Photo capture requires starting a (LED-lit) stream first; the capture LED
   is mandatory and firmware-enforced. Look-and-Ask is explicit and visible.
4. Only ONE third-party app may be registered in Developer Mode at a time.
5. Permission model: one-time app registration bounce through the Meta AI app,
   then per-capability grants (currently a single `CAMERA` permission) inside
   the Meta AI app. Mic/speakers use plain OS Bluetooth permissions. **[DOC]**

## 6. Terms assessment (not legal advice)

The Wearables Developer Terms & AUP govern use regardless of publishing. No
clause prohibits routing capture to a self-hosted AI backend; Meta's own
showcase partners (Aira, Seeing AI) do third-party AI on the same interfaces.
Prohibited: reverse engineering, interfering with normal product operation
(⇒ do not attempt to intercept/replace "Hey Meta"), data sale/surveillance
uses. A personal Developer-Mode companion app fits the documented pattern.
**[DOC clauses; INF assessment]**
