# Security & Privacy

## Where your data goes (and doesn't)

| Data | Path | Retention |
|---|---|---|
| Voice audio | glasses → phone (BT) → gateway `/transcribe` (LAN) → local Whisper | processed in memory; **never written to disk**; deleted with the request |
| Images (Look and Ask) | glasses → phone → `/vision/query` → local Ollama | in-memory only; references dropped before the response returns; never logged |
| Prompts & answers | gateway → local Ollama models on this host | transient session context in RAM (rolling 12 turns, 30-min idle expiry); nothing written to the Odysseus DB or ChromaDB in v1 |
| Transcripts | — | not stored unless the client opts in per-request (`store_transcript`, still RAM-only) |
| Memory | — | **no permanent memory writes in v1**; a later opt-in will go through the documented `/api/memory` proposal/approval interfaces only |
| Logs | host | metadata only: request ids, owner, model name, byte/char counts, error codes |

Delete controls: `DELETE /session/{id}` (drops context immediately),
device revocation, and process restart (all sessions are RAM-only).

## The Meta boundary — honest disclosure

Meta's software **is** still involved: the Meta AI app performs glasses
pairing and hosts the Developer-Mode registration; the Wearables SDK and the
glasses firmware handle the Bluetooth/camera transport; Meta's terms apply to
that transport. **AI inference, speech processing, memory, and tool use are
local to your host.** We do NOT claim "no data ever reaches Meta": device
telemetry, pairing metadata, and whatever the Meta AI app itself collects are
outside this project's control. What this project guarantees is that the
*assistant content path* (audio for transcription, images for vision, prompts,
generated responses) goes only phone → your host on your network. Verify with
network capture per TEST_PLAN.md §hardware before relying on stronger claims.

## Gateway hardening (implemented + tested)

- Single auth-exempt route (`/pair`), rate-limited, single-use hashed codes.
- Scope-restricted device tokens (`wearables` only) — no general API access.
- Read-only toolset (`web_search`, `web_fetch`) + hard deny-set; agent runs
  with `trusted_execution=False`, so Odysseus's safe-abstention /
  prompt-injection defenses remain active. The glasses channel can never
  execute shell/file/git/memory tools — it is not a remote shell.
- Request validation everywhere; payload caps (25 MiB audio, 10 MiB image,
  4000-char text) enforced mid-stream; per-owner rate limits.
- Errors normalized to stable codes; internal detail never leaks to devices.
- Spoken responses exclude model chain-of-thought and never read secrets,
  URLs, or code aloud (system prompt + transform layer + tests).

## Logging policy

Gateway log lines carry `[wearables]` + request id + counts only. Verified
live: prompts, answers, transcripts, image bytes, and raw tokens are absent
from gateway logs.

**Known host-level finding (pre-existing, outside this feature):**
`src/agent_loop.py` logs the latest user message at INFO
(`[agent-intent] latest='…'`) for *every* channel including the web UI.
Until that repo-wide line is demoted/truncated, host logs do contain prompt
text from the shared agent runtime. Recommended follow-up: truncate/redact at
that call site (one line), or run the host at WARNING in sensitive contexts.

## Secrets

No secrets in source or config examples. Pairing codes and device tokens are
hashed at rest, shown once. The Android app stores its credential in the
Android Keystore, never in plaintext prefs, and never embeds any API key.
Never use `ollama`/`local` development keys as mobile credentials.
