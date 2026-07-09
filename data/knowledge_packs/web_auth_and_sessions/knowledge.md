# Web Auth and Sessions
## Session vs token
- Server session: random opaque `session_id` in cookie; state lives server-side (Redis/DB). Revoke = delete row. Scales via shared store or sticky sessions.
- Token (JWT): self-contained, stateless; server verifies signature, no lookup. Trade-off: can't revoke before expiry without a denylist.
- Default to server sessions for browser apps; use tokens for stateless APIs / service-to-service.
## Cookies
- `HttpOnly`: JS can't read it — blocks XSS token theft. ALWAYS set on session cookies.
- `Secure`: HTTPS-only. `SameSite=Lax` (default) blocks cross-site POST CSRF while allowing top-level GET nav; `Strict` breaks inbound links; `None` requires `Secure` (needed for cross-origin/3rd-party).
- Scope with `Domain`/`Path`; set short `Max-Age` + rotate. Prefix `__Host-` forces Secure + Path=/ + no Domain (subdomain isolation).
## JWT
- Three base64url parts `header.payload.signature`. Payload is NOT encrypted — never put secrets in it.
- Sign HS256 (shared secret) or RS256/ES256 (private key signs, public verifies — prefer for multi-service). Verify `alg`, `exp`, `iss`, `aud` every request.
- Keep access tokens short (5–15 min). Refresh token (long-lived, HttpOnly cookie, stored server-side) mints new access tokens. Rotate refresh tokens on use + detect reuse (replay = revoke family).
- Revocation problem: valid signature = valid until `exp`. Mitigate with short expiry + denylist by `jti` for forced logout.
## OAuth2 / OIDC
- Authorization Code + PKCE for ALL clients now (SPAs and native included; implicit flow is dead). Flow: redirect to `/authorize` with `code_challenge` (S256 of `code_verifier`) → user consents → `code` returned → exchange `code`+`code_verifier` at `/token` for tokens.
- OIDC adds `id_token` (JWT with user identity) on top of OAuth2's access token. `scope=openid`. Validate `nonce` to bind to your session.
- `state` param = CSRF protection on the redirect; verify it matches on callback. Access token is for resource APIs, NOT for authenticating your own login.
## OAuth2 grant types
| Grant | Use for | Notes |
|---|---|---|
| Auth Code + PKCE | web SPA, native/mobile, server web apps | only interactive flow to use now; `code_challenge=S256` |
| Client Credentials | service-to-service (no user) | machine identity; `client_id`+`client_secret`, no refresh needed |
| Device Authorization | TVs, CLIs, input-constrained | user visits `verification_uri` + enters `user_code`; client polls `/token` |
| Refresh Token | renew access without re-login | rotate on use; long-lived, store server-side/HttpOnly |
- Dead/avoid: Implicit (token in URL fragment — leaks, no rotation) and Resource Owner Password Credentials (app sees the password — only legacy first-party).
- `scope` = coarse permission grant; audience (`resource`/`aud`) targets a specific API. Consent screen shows scopes to the user.
## JWT vs opaque tokens
- JWT (self-contained): no DB lookup to verify; carries claims. Cost: can't revoke pre-`exp`, bloats with claims, key rotation via `kid`+JWKS, stale claims until refresh.
- Opaque (random string): meaningless to client; server looks up state (introspection endpoint / session store). Instantly revocable, small; cost: a lookup per call.
- Common prod pattern: opaque token at the edge, exchanged for a short JWT internally; or JWT access token (short) + opaque refresh token (revocable).
## MFA / TOTP
- TOTP (RFC 6238): shared secret + 30s time step → 6-digit HOTP. Enroll via `otpauth://` URI in QR; accept ±1 step for clock skew. Store the secret encrypted; store one-time recovery codes hashed.
- WebAuthn/passkeys: phishing-resistant (origin-bound public-key); prefer over TOTP for high-value. SMS OTP is weakest (SIM-swap, interceptable) — avoid as primary.
- Prevent replay: mark a TOTP code used within its window. Step-up MFA on sensitive actions, not just login.
## Sessions across devices
- Model a session per device: store `(user_id, session_id, device, ip, created, last_seen)`; "log out everywhere" = delete all rows / bump a per-user `token_version` claim so old JWTs fail.
- Password change or reset MUST invalidate all existing sessions/refresh tokens. Surface an "active sessions" UI so users can revoke individually.
## Remember-me & rate limiting
- "Remember me" = long-lived selector/validator cookie (store validator hashed); on use, mint a fresh session. Rotate the token each use; never a permanent unhashed credential.
- Rate-limit login by IP AND by account; exponential backoff or temporary lockout after N fails. Prefer soft locks + CAPTCHA over hard locks (avoid attacker-driven account lockout DoS). Rate-limit password-reset and MFA endpoints too.
## SSO / SAML
- SAML: XML assertions, browser POST binding, IdP-signed. Validate the signature, `Audience`, `NotBefore`/`NotOnOrAfter`, and consume `InResponseTo` once (replay). Enterprise/legacy.
- OIDC is the modern equivalent (JSON/JWT); prefer for new SSO. SCIM handles user provisioning/deprovisioning alongside SSO.
## Token storage
- Access token: in memory (JS variable) — gone on reload, re-fetched via refresh cookie. Refresh token: `HttpOnly; Secure; SameSite` cookie only.
- localStorage/sessionStorage = readable by any XSS → token exfiltration; never store bearer tokens there. Cookies avoid JS read but need CSRF defenses.
## Password storage
- Hash with `argon2id` (preferred) or `bcrypt` (cost ≥ 12) or `scrypt`. NEVER MD5/SHA-256 raw — too fast, GPU-crackable.
- Salt is per-user and auto-embedded in the bcrypt/argon2 hash string. `bcrypt` truncates at 72 bytes — pre-hash long inputs.
- Compare with constant-time verify (library does this). Add a server-side pepper (secret, out of DB) for defense in depth.
## Common auth bugs -> Fix
- **JWT `alg: none` / algorithm confusion**: attacker sets `alg:none` or swaps RS256→HS256 using public key as HMAC secret. Fix: pin the expected algorithm explicitly in verify options; never trust header `alg`.
- **Missing `aud`/`iss` check**: token from another service/tenant accepted. Fix: verify audience and issuer.
- **Reading token without verifying signature**: decode ≠ verify. Fix: always `verify()`, never bare `decode()` for trust decisions.
- **JWT in localStorage**: XSS steals it. Fix: HttpOnly cookie for refresh; keep access token in memory only.
- **CSRF on cookie auth**: cookies auto-send cross-site. Fix: `SameSite=Lax/Strict` + CSRF token (double-submit or synchronizer) for state-changing requests. Token auth in `Authorization` header is immune to CSRF (not auto-sent).
- **Session fixation**: reuse pre-login session id. Fix: regenerate session id on privilege change (login).
- **No logout invalidation**: stateless JWT ignores logout. Fix: server session or short expiry + `jti` denylist.
- **Timing attack on user-exists**: different response for unknown user vs bad password. Fix: uniform error + constant-time path; always run a hash even when user missing.
- **Open redirect on OAuth `redirect_uri`**: attacker steals code. Fix: exact-match allowlist of redirect URIs, no wildcards.
- **Long-lived access tokens**: can't revoke. Fix: 5–15 min access + rotating refresh.
- **Refresh token theft undetected**: Fix: rotation + reuse detection revokes the whole token family.
- **Password change leaves old sessions live**: attacker keeps access after victim resets. Fix: invalidate all sessions/refresh tokens on password change/reset; bump `token_version`.
- **JWT clock skew rejects valid tokens**: strict `exp`/`nbf` at boundaries. Fix: small leeway (30–60s) in verify.
- **Key rotation breaks verification**: single signing key, no rollover. Fix: publish JWKS with `kid`; verifiers pick key by `kid`; overlap old+new during rotation.
- **Account-lockout DoS**: attacker locks victims by spamming bad passwords. Fix: soft lock + CAPTCHA/backoff, per-IP limits, don't hard-lock on remote failures.
- **TOTP replay**: same code used twice in its window. Fix: record last-used step per user; reject reuse.
- **SMS OTP as primary MFA**: SIM-swap/interception. Fix: prefer TOTP/WebAuthn; SMS only as fallback.
- **Overloaded scopes / confused deputy**: token minted for API A accepted by API B. Fix: bind tokens to an audience; each API verifies `aud`.
- **Logout only clears client**: server session/token still valid. Fix: server-side invalidate (delete session / denylist `jti` / revoke refresh).
- **Cookie without `__Host-` on shared domain**: subdomain can set/overwrite. Fix: `__Host-` prefix; isolate per-subdomain cookies.
- **Verifying ID token as access token (or vice-versa)**: `id_token` authenticates the user to *you*; access token is for resource APIs. Fix: don't send `id_token` to APIs; validate `nonce`/`aud=client_id` on `id_token`.
## Checklist
- Login: rate-limit + lockout/backoff; MFA (TOTP/WebAuthn) for sensitive accounts.
- Cookies: `HttpOnly; Secure; SameSite=Lax; __Host-` prefix.
- Transport: HSTS, TLS only. Tokens: short access, rotating refresh, verify sig+exp+aud+iss.
- Storage: argon2id/bcrypt cost≥12; never log tokens or password hashes.
