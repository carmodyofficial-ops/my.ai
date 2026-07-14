# my.ai Glasses — Wearables Companion

A private, hands-free AI companion for **Ray-Ban Meta Wayfarer** smart glasses,
powered entirely by the local **my.ai / Odysseus** system on your Ubuntu host.
Meta's cloud AI does not process or generate any assistant content; Meta's
software is still involved in device pairing and the supported
glasses↔phone link (see SECURITY_AND_PRIVACY.md for the exact boundary).

```
Ray-Ban Meta glasses
  → Meta Wearables Device Access Toolkit + standard Bluetooth (HFP mic / A2DP speakers)
  → my.ai Glasses Android companion app
  → authenticated LAN connection (paired device credential)
  → Odysseus Wearables Gateway  (/api/wearables/v1/*)
  → local models (Ollama), STT (faster-whisper), TTS (Kokoro), vision (qwen3.6/mistral-small)
  → streamed response → phone → glasses speakers
```

## Status (2026-07-12)

| Piece | State |
|---|---|
| Backend gateway (`/api/wearables/v1`) | **Implemented + live-validated** on the local host |
| Enrollment (one-time code → revocable device token) | **Live-validated** |
| Text conversation (SSE streaming, follow-ups, cancel) | **Live-validated** against local models incl. auto model routing |
| Look and Ask (vision) | **Live-validated** with `qwen3.6:27b` (local) |
| STT / TTS | Interfaces + honest `STT_UNAVAILABLE`/`TTS_UNAVAILABLE`; engines not yet installed (see LOCAL_MODEL_PIPELINE.md) |
| Android app | Skeleton with Meta SDK adapter + mock path (see INSTALL_ANDROID.md); **not hardware-validated** |
| iOS | Design only (IOS_FUTURE_PLAN.md) |

## Documents

- ARCHITECTURE.md — components, flows, Mermaid diagram
- META_SDK_CAPABILITY_MATRIX.md — what the official Meta toolkit does/doesn't allow (v0.8.0)
- PAIRING_AND_AUTH.md — enrollment, credentials, revocation
- SECURITY_AND_PRIVACY.md — data handling, log policy, Meta boundary disclosure
- THREAT_MODEL.md
- LOCAL_MODEL_PIPELINE.md — STT/TTS/LLM/vision adapters and how to enable engines
- TEST_PLAN.md — automated coverage + hardware checklist
- INSTALL_ANDROID.md — building and running the companion app
- IOS_FUTURE_PLAN.md
- OPERATIONS_RUNBOOK.md — start/stop/health/diagnostics
- ENGINEERING_TURNOVER.md — what was done, validated, and what remains
- openapi.yaml — API contract for `/api/wearables/v1`

## Quickstart (backend only, from the repo root)

```bash
# gateway ships inside the odysseus app; run the health script:
scripts/wearables/wearables_healthcheck.sh
# pair a device (admin): POST /api/wearables/v1/pairings, then exchange the
# one-time code from the phone at POST /api/wearables/v1/pair
```

## Non-goals / honesty notes

- No firmware modification, jailbreaking, or Meta AI replacement at the OS
  level. "Hey Meta" remains Meta's. First-release activation is push-to-talk
  in the companion app (the current SDK exposes no glasses gesture/wake hook
  for third-party apps on camera-only glasses).
- The Meta toolkit is a **Developer Preview**: apps run via Developer Mode on
  your own account; public distribution is not yet available.
- Remote (off-LAN) access is out of scope for v1; the transport interface is
  designed so a user-controlled VPN (e.g. WireGuard/Tailscale) can be added
  without app changes.
