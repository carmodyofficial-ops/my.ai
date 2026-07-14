# Pairing & Authentication

## Credential model

Device credentials are standard Odysseus **`ody_` API tokens** (bcrypt hash +
8-char prefix at rest, raw value shown once) with the dedicated scope
**`wearables`** — so:

- the auth middleware treats them like every other token (same cache, same
  revocation), and they appear in **Settings → API tokens**;
- the scope means a stolen glasses credential **cannot** call the general
  chat/admin API — only `/api/wearables/v1/*` accepts it;
- the token's `owner` is the enrolling admin, so glasses conversations are
  attributed to the same human as the desktop UI (`effective_user`).

## Enrollment flow (two-step, replay-resistant)

```
Admin (browser, cookie session)                    Phone (no credential yet)
──────────────────────────────                     ─────────────────────────
POST /api/wearables/v1/pairings
  → { code: "wpair_…", expires_in: 300,
      payload {v,kind,host,port,tls,code,
               cert_sha256?}, qr }
      # cert_sha256 (tls only): SHA-256 of the
      # advertised cert's DER — the app pins it
      # (self-signed LAN cert has no trust anchor;
      # the QR is the trust bootstrap). Cert path
      # env MYAI_WEARABLES_TLS_CERT, default
      # data/lan-cert.pem.
        │  QR shown on desktop
        └────────────── scan ─────────────────────▶ POST /api/wearables/v1/pair
                                                      { code, device_name }
                                                      → { token: "ody_…" (once),
                                                          token_id, owner,
                                                          scope: "wearables" }
                                                      stored in Android Keystore
```

Properties (all covered by tests and validated live 2026-07-12):

- Codes are **single-use** (atomically consumed), **TTL 300 s**, stored only
  as **sha256**, capped at 20 pending, and void on app restart.
- `POST /pair` is the only auth-exempt route; it is rate-limited
  **5/min/IP** and returns a uniform `PAIRING_CODE_INVALID` on any failure.
- Minting is **admin-cookie POST only** (CSRF-safe under SameSite=Lax, same
  posture as `companion/` and `POST /api/tokens`).
- Token cache is invalidated on mint/revoke, so credentials work/stop
  **immediately** in the serving process.

## Revocation

- `GET /api/wearables/v1/devices` (admin) lists devices (no secret material).
- `DELETE /api/wearables/v1/devices/{token_id}` (admin) deactivates.
- Also visible/revocable in **Settings → API tokens** (names are prefixed
  `wearable:`).
- **Known limitation:** the token cache is per-process. Revoking through a
  *different* process (e.g. a second dev instance sharing the DB) does not
  invalidate the production process's in-memory cache until its next
  invalidation/restart. In the normal single-process deployment revocation is
  immediate. Verified live in both directions.

## Network placement

- All Odysseus/infra ports bind to **127.0.0.1** on the host; the mobile API
  is only the gateway through the app's published port (currently
  `127.0.0.1:7001` → LAN exposure is an explicit operator step: set
  `APP_BIND` to the LAN interface **and** put TLS in front — see
  OPERATIONS_RUNBOOK.md).
- Ports 11434 (Ollama), 8787 (ProjectForge), 8100 (ChromaDB), 8080 (SearXNG)
  are never exposed to the phone.
- `MYAI_WEARABLES_ADVERTISE_HOST/PORT/TLS` set the address embedded in
  pairing QR payloads (inside Docker the auto-detected address is the
  container network, which a phone cannot reach). Configured live:
  payloads carry `{"host":"192.168.1.50","port":7443,"tls":true}` →
  the app dials `https://…:7443` (the TLS lan_proxy).
- TLS: terminate at a reverse proxy (nginx/caddy) or use a private overlay
  (Tailscale/WireGuard). The Android client pins the configured host and
  refuses cleartext except to RFC1918 hosts explicitly confirmed by the user
  during setup. Remote/off-LAN access is out of scope for v1.
- The pairing payload never contains a long-lived secret — only the 5-minute
  single-use code; interception after redemption is worthless.
