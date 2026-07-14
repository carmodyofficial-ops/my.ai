# iOS Future Plan

No iOS build has been compiled (no macOS/Xcode in this environment). This is
the design so an iOS counterpart is a port, not a redesign.

## Stack

Swift + SwiftUI + async/await + URLSession (SSE via `URLSession.bytes`) +
Keychain (device credential) + native Meta Wearables DAT Swift Package
(`facebook/meta-wearables-dat-ios`: `MWDATCore`, `MWDATCamera`,
`MWDATMockDevice`; iOS 15.2+).

## Structure (mirrors Android 1:1)

| Android | iOS |
|---|---|
| `WearablesAdapter` interface | `WearablesAdapting` protocol |
| `MetaDatAdapter` / `MockWearablesAdapter` | `MetaDatAdapter` / `MockWearablesAdapter` |
| `GatewayClient` (OkHttp SSE) | `GatewayClient` (URLSession bytes/SSE) |
| `CredentialStore` (Keystore) | `CredentialStore` (Keychain, `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`) |
| `ConnectionReducer` (pure) | same reducer, Swift port — unit-testable |
| Foreground service for audio | `UIBackgroundModes`: `bluetooth-peripheral`, `external-accessory`, `audio` |

The backend contract (`openapi.yaml`) is platform-neutral; nothing
server-side changes for iOS.

## iOS-specific work items

1. Info.plist `MWDAT` dict (`AppLinkURLScheme`, `MetaAppID`, `ClientToken`,
   `TeamID`) + `UISupportedExternalAccessoryProtocols` = `com.meta.ar.wearable`.
2. Audio: `AVAudioSession` category `.playAndRecord`, mode `.voiceChat`, with
   `allowBluetooth` (HFP capture) / `allowBluetoothA2DP` (TTS out); handle
   route-change + interruption notifications (calls, Siri).
3. TTS playback via `AVAudioPlayer` (gateway audio) with `AVSpeechSynthesizer`
   as the labeled on-device fallback.
4. ATS exception only for the user-confirmed RFC1918 host, or ship the local
   CA profile flow; prefer certificate pinning of the host cert.
5. Mock Device Kit UI tests via `MWDATMockDevice` + `MockDeviceTestClient`.

## Explicit non-claims

Nothing in this file has been executed. Treat every line as *planned* until a
macOS build validates it.
