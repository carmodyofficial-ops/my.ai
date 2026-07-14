# Operations Runbook — Wearables Gateway

## Where it runs

The gateway is part of the main Odysseus app (no separate process). Deploying
a code change = restart the odysseus compose service:

```bash
cd ~/odysseus && docker compose restart odysseus   # ~30 s startup
```

## Health

```bash
scripts/wearables/wearables_healthcheck.sh          # end-to-end component check
curl -s http://127.0.0.1:7001/api/health            # app liveness (no auth)
# authenticated (needs a wearables token or admin cookie):
curl -s -H "Authorization: Bearer $TOK" http://127.0.0.1:7001/api/wearables/v1/capabilities
```

`/capabilities` is the source of truth: it reports live STT/TTS/LLM/vision
availability. `stt/tts available:false, provider:disabled` is the expected
state until speech engines are enabled (LOCAL_MODEL_PIPELINE.md).

## Pairing a new phone

1. Browser (admin): `POST /api/wearables/v1/pairings` (the app UI can call
   this; a curl with the admin cookie works too). Show QR / code.
2. Phone: scan within 5 minutes; the app exchanges it at `/pair`.
3. Verify under Settings → API tokens (`wearable:<name>`), or
   `GET /api/wearables/v1/devices`.

Revoke: `DELETE /api/wearables/v1/devices/{token_id}` or the tokens UI.
Revocation is immediate in the serving process.

## LAN exposure — CONFIGURED 2026-07-12 (TLS proxy)

The app stays loopback-only (`APP_BIND=127.0.0.1`); LAN entry is the repo's
lan_proxy running as two user services:

| Service | Listen | Mode | Purpose |
|---|---|---|---|
| `myai-lan-proxy.service` | 0.0.0.0:7000 | **plain** (pre-existing) | legacy phone/browser access — disable after migrating: `systemctl --user disable --now myai-lan-proxy` |
| `myai-lan-proxy-tls.service` | 0.0.0.0:**7443** | **TLS** (self-signed `data/lan-cert.pem`, SAN 192.168.1.50) | wearables/mobile entry point |

Env files: `~/.config/myai-lan-proxy.env` / `~/.config/myai-lan-proxy-tls.env`.
Cert renewal / IP change: `MYAI_LAN_IP=<ip> scripts/gen_self_signed_cert.sh`
then `systemctl --user restart myai-lan-proxy-tls`.

`.env` (applied): `SECURE_COOKIES=true`,
`MYAI_WEARABLES_ADVERTISE_HOST=192.168.1.50`,
`MYAI_WEARABLES_ADVERTISE_PORT=7443`, `MYAI_WEARABLES_ADVERTISE_TLS=true` —
pairing QR payloads now dial `https://192.168.1.50:7443` (`"tls": true`).

Still true: no port-forwarding/UPnP; 11434/8787/8100/8080 stay loopback or
docker-bridge only. Firewall not modified (ufw state needs sudo to inspect —
if LAN devices can't reach 7443, check/open it there).

## Speech services

- **TTS sidecar**: `myai-tts-sidecar.service` (user unit) → Kokoro on
  `172.17.0.1:8123`; logs `journalctl --user -u myai-tts-sidecar`.
- **STT**: faster-whisper inside the odysseus container.
- **After a container RECREATE** (compose config change — a plain restart is
  fine): rerun `docker exec odysseus-odysseus-1 pip install faster-whisper
  pytest pytest-asyncio`, or rebuild the image with
  `--build-arg INSTALL_OPTIONAL=true` to make it permanent.

## Tunables (env)

| Var | Default | Meaning |
|---|---|---|
| `ODYSSEUS_STT_MAX_AUDIO_BYTES` | 25 MiB | transcription upload cap |
| `ODYSSEUS_WEARABLES_IMAGE_MAX_BYTES` | 10 MiB | vision upload cap |
| `MYAI_WEARABLES_ADVERTISE_HOST` | (auto) | host embedded in pairing QR |

Settings (`data/settings.json`): `wearables_vision_model` (else auto-detect),
`stt_provider/stt_model`, `tts_provider/...`.

## Diagnostics

```bash
scripts/wearables/wearables_diag.sh    # redacted bundle → /tmp/wearables_diag_<ts>.txt
docker logs --since 1h odysseus-odysseus-1 | grep '\[wearables\]'
```

Gateway log lines are metadata-only. Sessions are RAM-only: a restart clears
all conversation context (by design) and voids unconsumed pairing codes.

## Failure triage

| Symptom (client error code) | Check |
|---|---|
| `MYAI_HOST_UNREACHABLE` (app-side) | app container up? phone on same network? APP_BIND/advertise host right? |
| 401 / `DEVICE_CREDENTIAL_REVOKED` | token revoked or DB restored — re-pair |
| `LLM_UNAVAILABLE` | Ollama up on the host? `curl 127.0.0.1:11434/api/tags`; default endpoint configured? |
| `STT_UNAVAILABLE` / `TTS_UNAVAILABLE` | providers disabled — expected until engines installed |
| `VISION_MODEL_NOT_CONFIGURED` | no vision-capable model in Ollama; install one or set `wearables_vision_model` |
| Slow first vision/complex answer | cold model load (tens of seconds); subsequent calls are fast |
| 429 | rate limits: pair 5/min/IP, respond 30/min, media 20/min per owner |
