# Test Plan

## Automated backend tests (in `tests/`, run in the container)

```bash
docker exec odysseus-odysseus-1 python3 -m pytest \
  tests/test_wearables_pairing.py \
  tests/test_wearables_sessions_spoken.py \
  tests/test_wearables_routes.py -q
```

59 tests, all green 2026-07-12. Coverage map:

| Contract | Test(s) |
|---|---|
| Pairing single-use / TTL / hashed-at-rest / cap / cross-owner | test_wearables_pairing.py |
| Device token bcrypt at rest, scope, cache invalidation | test_wearables_pairing.py |
| Revocation only touches wearables rows; unknown → 404 | test_wearables_pairing.py, test_wearables_routes.py |
| Scope gate (bearer needs `wearables`; unauthenticated 401) | test_wearables_routes.py |
| Enrollment exchange happy path + replay + rate limit | test_wearables_routes.py |
| Request validation, payload caps (413), rate limits (429) | test_wearables_routes.py |
| SSE stream shape (meta → deltas → spoken → done → [DONE]) | test_wearables_routes.py |
| Thinking-delta exclusion from voice/history (live-found bug) | test_respond_excludes_thinking_from_spoken |
| Follow-up context threading; owner-scoped sessions/cancel/delete | routes + sessions tests |
| Cancellation mid-stream; stream error → SSE error event, clean termination | test_wearables_routes.py |
| STT/TTS/vision adapter mocks incl. unavailable states | test_wearables_routes.py |
| Capability discovery honesty | test_capabilities_honest_reporting |
| Log redaction (no prompts/transcripts/answers in logs) | test_logs_never_contain_prompt_or_transcript |
| Spoken transform (markdown/code/URL stripping, truncation) | test_wearables_sessions_spoken.py |
| Privacy no-storage mode; idle pruning; per-owner caps | test_wearables_sessions_spoken.py |

Regression safety: the previously-passing suites for every touched area
(api tokens, companion, auth hardening, upload limits, security headers,
webhook auth-exemption) re-run green — 109 tests.

## Live validation (real services, no mocks) — executed 2026-07-12

Recorded with commands + output in ENGINEERING_TURNOVER.md:
enrollment → replay rejection → capabilities → streamed 120B/20B responses
with auto-routing → cancellation → STT/TTS honest 503s → real vision answer
(qwen3.6:27b) → revocation → log redaction.

## Android tests (in `apps/myai-glasses-android/`)

- Unit (JVM, no device): `ConnectionReducerTest`, `SseParserTest`,
  `SpokenPolicyTest`, `PairingPayloadTest` — `./gradlew test`.
- Instrumented + Mock Device Kit: mock-glasses workflow (pair → stream →
  photo), permission flows, background audio lifecycle — requires the Meta
  SDK artifacts + an Android device/emulator (not runnable on this host; see
  INSTALL_ANDROID.md).

## Hardware validation checklist (pending — requires physical glasses + phone)

1. Meta AI app V272+, glasses firmware V127+, Developer Mode ON, app
   registered in Wearables Developer Center.
2. HFP capture from glasses mic → `/transcribe` (once STT engine enabled).
3. A2DP playback of `/speech` audio through glasses speakers.
4. Profile toggle latency (HFP↔A2DP) between listen/speak turns.
5. Look-and-Ask via DAT stream + `capturePhoto()` → `/vision/query`.
6. Barge-in behavior; phone-call interruption; BT disconnect recovery.
7. Battery drain over a 30-min conversation session.
8. **Network capture** (pcap on phone/router) proving assistant content flows
   only phone→host during use.
