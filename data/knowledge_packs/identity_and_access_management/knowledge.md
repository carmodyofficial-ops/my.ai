# Identity & Access Management (IAM)

## Core distinction
- **Authentication (AuthN)** = *who are you* (verify identity: password + MFA, passkey, cert). **Authorization (AuthZ)** = *what may you do* (permissions on resources). They are separate layers — a valid token proves identity, **not** entitlement. Enforce AuthZ server-side on every request/object.
- **Identification** (claimed identity) → AuthN (proof) → AuthZ (policy) → **Audit** (log who did what).

## OAuth2 — delegated authorization
- Roles: **resource owner** (user), **client** (app), **authorization server (AS)**, **resource server (API)**. OAuth2 issues **access tokens** to call APIs on the user's behalf — it is **authorization/delegation, NOT authentication** (that's OIDC's job).
- **Grant types**:
  - **Authorization Code + PKCE** — the default for *all* interactive apps now (web, SPA, mobile). Front channel returns a short-lived `code`; back channel swaps it for tokens.
  - **PKCE** (`code_challenge`/`code_verifier`, S256): binds the code to the client that started the flow → defeats authorization-code interception. Mandatory for public clients (SPA/mobile, no secret); recommended for all.
  - **Client Credentials** — machine-to-machine (no user), client authenticates with its own creds.
  - **Refresh token** — obtains new access tokens; rotate with reuse detection.
  - **Device Authorization** — input-constrained devices (TVs).
  - **Deprecated: Implicit** (tokens in URL fragment) and **Resource Owner Password** (app handles raw creds) — do not use.
- **Scopes** = coarse consent labels; not a substitute for API-side authorization. Prefer short-lived access tokens (mins) + refresh rotation. Use **PAR** and **sender-constrained tokens (DPoP / mTLS)** to harden against token theft.

## OIDC — authentication on top of OAuth2
- Adds the **ID token** (a signed **JWT** about the authentication event) + `/userinfo` + discovery (`.well-known/openid-configuration`) + JWKS.
- **ID token vs access token — do not confuse**: ID token = proof of *who authenticated*, audience = your client, consumed by *your app*. Access token = bearer credential for *calling an API*, audience = the API. **Never send an ID token to an API; never use an access token to identify the user in your app.**
- Validate ID token: signature (JWKS `kid`), `iss`, `aud` == your client_id, `exp`/`iat`, and **`nonce`** matches the one you sent (replay defense). `sub` = stable user id (email is not).

## SAML — enterprise SSO (XML)
- Roles: **IdP** (asserts identity), **SP** (your app, relies on it). Browser-redirect/POST of a **SAML assertion** (signed XML with subject + attributes + conditions).
- SP validates: **XML signature** on assertion/response, `Issuer`, `Audience`, `NotBefore`/`NotOnOrAfter`, `Recipient`, and **replay** (cache the assertion ID). Prefer signing the assertion.
- Still dominant in enterprise; OIDC is the modern equivalent for new apps.

## SSO & federation
- **SSO**: authenticate once, access many apps (shared IdP session).
- **Federation**: trust identities from another domain/IdP (SAML/OIDC) so you don't manage those credentials. Central IdP = single control point for onboarding/**offboarding** (kill one account, revoke everywhere) and MFA policy.

## JWT — validate correctly or it's worthless
- Structure: `header.payload.signature`, base64url — **payload is readable, not encrypted**. No secrets/PII in claims.
- Standard claims: `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`.
- **Validation rules (all of them)**: verify **signature** first; **pin the expected `alg`** server-side (reject `alg:none`; reject RS↔HS **algorithm confusion** where a public key is fed as an HMAC secret); check `exp`/`nbf`; check `iss` and **`aud`** (a token for service A must be rejected by service B); rotate signing keys via **JWKS `kid`**.
- Tradeoff: JWTs are **stateless → not revocable before `exp`**. Keep access tokens short (≤15 min) + refresh rotation, or keep a revocation/`jti` denylist for logout/compromise.

## Sessions
- Server session cookie: `HttpOnly; Secure; SameSite=Lax`, `__Host-` prefix; instantly revocable; **rotate session ID on login and privilege change** (session fixation). Idle + absolute timeouts.
- Browser token storage: `localStorage` is XSS-readable (exfiltratable) — prefer refresh token in **HttpOnly cookie** + access token in memory; cookies need CSRF defenses (SameSite + token/custom header).

## Authorization models
- **RBAC** — permissions via **roles** (`admin`, `editor`). Simple, auditable; explodes with edge cases ("role explosion").
- **ABAC** — policy over **attributes** (user dept, resource owner, time, IP, device posture). Flexible, dynamic; harder to reason about/test. Often expressed in a policy engine (OPA/Rego, Cedar).
- **ReBAC** — permissions from **relationships** in a graph ("user is *editor of* doc that is *in* folder shared with team") — Google Zanzibar model. Great for sharing/hierarchies.
- Often layered: RBAC for coarse gates, ABAC/ReBAC for fine-grained + ownership. **Least privilege**: grant minimum needed. **Separation of duties**: no single identity can request *and* approve. **Deny by default**.

## MFA, passkeys, WebAuthn
- Factors: something you know / have / are. **Phishing-resistant** factors win: **WebAuthn/FIDO2 passkeys** (origin-bound public-key credential, private key in authenticator/TPM/Secure Enclave — nothing shared to phish). Prefer over TOTP; prefer TOTP/push over **SMS** (SIM-swap, interceptable). Guard against **MFA-fatigue/push-bombing** (number matching).
- Passkeys can be **synced** (cloud, cross-device UX) or **device-bound** (higher assurance).

## Zero trust
- "Never trust, always verify." No implicit trust from network location (no "inside = trusted"). **Per-request** authentication + authorization, verify **device posture + identity**, **least-privilege** + micro-segmentation, assume breach, log everything. Short-lived credentials over long-lived; policy decision point (PDP) + enforcement point (PEP).

## Secrets & machine identity
- No hardcoded/committed secrets. Use a **secrets manager/vault** or cloud KMS; inject at runtime; **short-lived, auto-rotated** creds. Workload identity (SPIFFE/SVID, cloud instance roles, OIDC federation for CI) instead of static API keys. Audit + rotate on any exposure.

## Directories, provisioning, lifecycle
- **Directory** = source of truth for identities/groups: LDAP / Active Directory (on-prem, Kerberos/NTLM), Entra ID / Okta / cloud IdPs. Apps federate to it rather than storing passwords.
- **Provisioning**: **SCIM** (System for Cross-domain Identity Management) automates create/update/**deprovision** of users+groups from IdP → app. Manual provisioning = orphaned accounts + audit gaps.
- **Joiner-Mover-Leaver**: onboard with least privilege, adjust on role change (avoid **privilege creep**), and **deprovision immediately** on exit (biggest real-world gap). **Access reviews / recertification** periodically prune stale grants.
- **Token types recap**: access token (call APIs), refresh token (renew, rotate), ID token (who authenticated). Bearer tokens = whoever holds it can use it → protect in transit + at rest, short TTL, consider sender-constrained (DPoP/mTLS).

## Delegation & consent
- **Delegated** (on-behalf-of user) vs **application** (app's own identity, client credentials) permissions — a common privilege-escalation source when app perms are over-granted.
- **Consent**: user/admin approves scopes; watch **illicit consent grant** attacks (malicious app requesting broad scopes). Prefer admin-consent for high-privilege scopes and incremental/just-in-time consent.
- **Token exchange** (RFC 8693) for service chains — downscope, don't forward a powerful token downstream.

## Gotchas -> Fix
- **AuthN treated as AuthZ** ("logged in" = allowed) -> enforce per-resource ownership/role checks server-side.
- **Implicit / password grant** -> Authorization Code + PKCE.
- **Missing/incorrect `aud` check** (token minted for one service accepted by another) -> validate `aud` and `iss` on every token.
- **`alg:none` / RS→HS algorithm confusion** -> pin allowed algorithm; never derive HMAC key from a public key.
- **Trusting decoded JWT without signature verify** -> verify signature + expiry first, always.
- **Long-lived, non-revocable access tokens** -> short TTL + refresh rotation w/ reuse detection; denylist for logout/compromise.
- **Over-broad roles / standing admin** -> least privilege, scoped roles, just-in-time elevation, periodic access reviews.
- **No offboarding via IdP** -> central federation; deprovision on termination revokes all app access.
- **Tokens in URLs / logs / localStorage** -> back-channel exchange, HttpOnly cookies, scrub logs.
- **SAML/OIDC without full assertion validation** (signature, audience, timestamps, replay/nonce) -> validate all conditions; cache assertion IDs / check nonce.
- **SMS OTP as primary MFA** -> WebAuthn passkeys or TOTP; SMS only as fallback.
- **Hardcoded API keys / static machine creds** -> vault + workload identity + rotation.
- **Session ID not rotated on login** -> regenerate on auth and privilege change.
