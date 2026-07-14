# Local Model Pipeline

All inference is local. The gateway consumes existing Odysseus adapters and
reports honest availability via `/capabilities` — the app never guesses.

## Text (working today)

- Endpoint resolution: `src/endpoint_resolver.resolve_endpoint("default", owner)`
  → currently Ollama `http://host.docker.internal:11434/v1` (OpenAI-compat).
- Per-turn auto routing (`src/model_router.py`): simple → `gpt-oss:20b`,
  complex → `seamon67/GPT-OSS-Heretic:v2-120b`, coding → `qwen3-coder:30b`
  (same policy as the web UI; verified live through the gateway).
- Streaming: real token streaming end-to-end (agent loop → SSE). No fake
  streaming anywhere; if an endpoint can't stream, the agent loop falls back
  and the client still gets a single final frame.

## Vision (working today)

- Resolution order: `wearables_vision_model` setting → auto-detect.
  Auto-detect asks **Ollama itself** (`/api/show` capabilities) — we never
  assume multimodality from a model name. Preference: `qwen3.6:27b`, then
  `mistral-small3.2:24b`, then any vision-capable installed model; result
  cached 10 min.
- If nothing qualifies: `503 VISION_MODEL_NOT_CONFIGURED` (explicit state,
  also shown in `/capabilities`). To configure manually:
  `settings.json: "wearables_vision_model": "qwen3.6:27b"`.
- Query path: base64 data-URI in OpenAI-compat `image_url` content →
  `llm_call_async` (bypasses tools; temperature 0.2; 700 max tokens).
- Live-validated 2026-07-12: `qwen3.6:27b` answered a fixture image in 56 s
  cold (model load) — warm responses are a few seconds. The phone should
  downscale/compress to ≤ ~1280 px JPEG before upload (10 MiB cap).

## STT — ENABLED & live-validated (2026-07-12)

`stt_provider = "local"` with **faster-whisper `base`** (CTranslate2, CPU
int8 — the container has no GPU; aarch64 wheels exist for the container's
py3.14). Measured: ~1.3 s for a 6.4 s utterance, warm. Accuracy verified by
round-tripping the gateway's own TTS output near-verbatim.

**Persistence caveat:** the engine was pip-installed into the running
container; a container *recreate* drops it. Durable fix: rebuild the image
with `--build-arg INSTALL_OPTIONAL=true` (faster-whisper is in
`requirements-optional.txt`); quick fix after recreate:
`docker exec odysseus-odysseus-1 pip install faster-whisper pytest pytest-asyncio`.

## TTS — ENABLED via host sidecar & live-validated (2026-07-12)

In-container Kokoro is **not possible today**: kokoro→misaki→**spacy has no
py3.14 wheels** and fails to build. (The CPU-fallback patch in
`services/tts/tts_service.py` remains correct and will activate if a future
image gets a compatible python.)

Instead the repo's `endpoint:<id>` provider is used, per the established
sidecar pattern (cf. myai-ollama-bridge-proxy):

- `scripts/wearables/tts_sidecar.py` — Kokoro-82M (CPU) behind an
  OpenAI-compatible `POST /v1/audio/speech`, running from a host py3.12 venv
  (`~/myai-tts/venv`), bound to the docker-bridge IP `172.17.0.1:8123`
  (host-local, not LAN-routable).
- systemd user unit `deploy/myai-tts-sidecar.service` (enabled, running).
- `ModelEndpoint` row `ttskokoro` → `http://host.docker.internal:8123/v1`;
  settings: `tts_provider="endpoint:ttskokoro"`, voice `af_heart`.

Measured: cold model load ~50 s (one-time); warm synthesis ~1.1 s for a
6-second utterance; output 24 kHz mono WAV (callers detect format from magic
bytes). If the sidecar is down the gateway honestly returns
`503 TTS_UNAVAILABLE`, and the phone may fall back to on-device Android TTS
**clearly labeled as a fallback** — no cloud speech APIs, ever.

## Adapter interfaces (mobile-facing stability)

The mobile app depends only on the HTTP contract (`openapi.yaml`):
`/transcribe`, `/respond`, `/speech`, `/vision/query`, `/capabilities`.
Engines can be swapped host-side (settings only) without any app change.
