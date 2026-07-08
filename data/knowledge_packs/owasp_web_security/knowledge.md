# OWASP Web Security

## XSS: types + CSP
- Reflected (payload in the request echoed back), stored (persisted, served to others), DOM-based (sink like `innerHTML`/`document.write`/`eval` fed by `location.hash`/user data — never hits the server).
- Defense 1: contextual output encoding — HTML-encode for element content, attribute-encode in attributes, JS-encode in scripts. Frameworks (React JSX, Vue templates) auto-escape; the escape hatches are the danger: `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `insertAdjacentHTML`.
- Sanitize rich HTML with DOMPurify (`DOMPurify.sanitize(html)`) — never regex-strip tags yourself.
- `javascript:` URLs in `href`/`src` bypass HTML escaping — allowlist URL schemes (http/https/mailto).
- CSP as backstop: `Content-Security-Policy: script-src 'self' 'nonce-<random>'; object-src 'none'; base-uri 'none'` — nonce-based with `'strict-dynamic'` beats domain allowlists (which are widely bypassable via JSONP/Angular gadgets on allowed CDNs). `unsafe-inline` neuters CSP. Roll out with `Content-Security-Policy-Report-Only` + `report-to` first.

## CSRF
- Attack: victim's browser auto-attaches cookies to cross-site requests (form posts, top-level navigations).
- Defenses (layer them): `SameSite=Lax` cookies (default in Chrome; Lax still sends on top-level GET navigations — never mutate state on GET), synchronizer tokens (per-session token in a hidden field, server compares), or double-submit cookie (token in cookie + header, server matches).
- SPAs with cookie auth: require a custom header (e.g., `X-CSRF-Token`) — cross-site HTML forms can't set custom headers; verify `Origin`/`Sec-Fetch-Site` headers server-side as an extra check.
- Pure `Authorization: Bearer` header auth (no cookies) is inherently CSRF-immune.

## Injection
- SQL: parameterized queries / prepared statements ONLY — `db.query('SELECT * FROM users WHERE id = $1', [id])`. String concatenation is the vulnerability; ORMs are safe until you use raw fragments (`.raw()`, `$queryRawUnsafe`).
- Command injection: never build shell strings from input; use exec APIs with arg arrays (`execFile('convert', [input])`), no `shell: true`.
- Path traversal: resolve then verify: `const p = path.resolve(base, name); if (!p.startsWith(base + path.sep)) reject`.
- NoSQL: reject object-typed input where strings are expected (`{ $gt: '' }` in Mongo queries) — validate types with zod/joi at the boundary.

## Broken access control (OWASP #1)
- IDOR: `/api/orders/123` fetched by any logged-in user — every object access must check ownership/tenancy server-side: `WHERE id = $1 AND user_id = $2`, not just authentication.
- Deny by default; enforce authorization in one middleware/layer, not per-handler ad hoc. Client-side hiding of buttons is not access control.
- Missing function-level checks: admin routes protected only by "the UI doesn't link there". Verify role on the server per request.
- Mass assignment: `User.update(req.body)` lets attackers set `role: 'admin'` — allowlist fields explicitly (DTOs, `pick()`).
- Unguessable IDs (UUIDs) reduce enumeration but are NOT authorization.

## SSRF
- Attack: server fetches a user-supplied URL → reaches internal services/cloud metadata (`http://169.254.169.254/latest/meta-data/`).
- Defenses: allowlist hosts/schemes; resolve DNS and block private/link-local/loopback ranges (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, ::1) — and re-check at connection time (DNS rebinding); disable redirects or re-validate each hop; on AWS require IMDSv2 (session tokens).
- Don't forget indirect fetchers: webhooks, PDF/image renderers, URL previews, importers.

## Security headers (baseline set)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS — HTTPS only).
- `X-Content-Type-Options: nosniff`; `X-Frame-Options: DENY` or CSP `frame-ancestors 'none'` (clickjacking).
- `Referrer-Policy: strict-origin-when-cross-origin`; `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- CORS is not a security header for your server — `Access-Control-Allow-Origin: *` with `credentials` is invalid anyway; never reflect arbitrary `Origin` with credentials allowed.

## Cookies & sessions vs JWT
- Session cookie flags, all of them: `HttpOnly; Secure; SameSite=Lax` (or `Strict`); `__Host-` prefix (requires Secure, no Domain, Path=/) pins the cookie against subdomain planting.
- Server sessions: revocable instantly, tiny cookie; rotate session ID on login (session fixation) and on privilege change.
- JWT pitfalls: cannot be revoked before `exp` (keep access tokens ≤15 min + refresh-token rotation w/ reuse detection); `alg: none`/algorithm-confusion attacks (pin the algorithm server-side, verify not just decode); don't put secrets/PII in the payload (base64, not encrypted); validate `iss`/`aud`/`exp`.
- Token storage in browsers: localStorage is XSS-readable; HttpOnly cookies are XSS-proof for exfiltration but need CSRF defenses. Common compromise: refresh token in HttpOnly cookie, short-lived access token in memory.

## File upload safety
- Validate server-side: allowlist extensions AND verify magic bytes/content type (don't trust client `Content-Type`); cap size before buffering.
- Store outside the webroot (or object storage) under server-generated names (never user filename — traversal `../../` and weird chars); strip EXIF from images.
- Serve downloads with `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, and ideally from a separate sandbox domain — an uploaded HTML/SVG served inline on your origin = stored XSS (SVG executes scripts).
- Re-encode images (sharp/ImageMagick with policy hardening) to destroy polyglot payloads.

## Supply chain, secrets, logging
- Dependencies: `npm audit` catches known CVEs only; pin with lockfiles, enable Dependabot/Renovate, beware typosquats and postinstall scripts (`npm i --ignore-scripts` in CI where possible).
- Secrets never in git or client bundles: env vars + secret manager; rotate anything ever committed (git history is forever); scan with gitleaks/trufflehog in CI.
- Security logging: log authn failures, authz denials, input-validation rejections with user/IP/time — but never log passwords, tokens, session IDs, or full card numbers.
- Rate limit per-account AND per-IP on login/reset/OTP; add exponential lockout or CAPTCHA after N failures; compare passwords with constant-time functions (bcrypt/argon2 verify does this).

## Gotchas -> Fix
- **React app "safe from XSS" but renders markdown**: markdown → HTML then `dangerouslySetInnerHTML` — run DOMPurify on the output.
- **CSRF token checked only on POST**: state changes via PUT/DELETE/GET slip through — enforce on all mutating methods and never mutate on GET.
- **`JSON.parse` of JWT payload treated as verified**: decoding is not verifying — use the library's `verify()` with pinned algorithm and audience.
- **Login has rate limiting, password reset doesn't**: enumerate/brute-force via reset and login-error differences — uniform errors + rate limit all auth endpoints.
- **CORS "fixed" by reflecting Origin**: with `Allow-Credentials: true` this grants any site authenticated API access — strict allowlist.
- **Internal-only admin protected by IP allowlist alone**: SSRF or proxy misconfig bypasses it — require real authn/authz too.
- **Error pages leak stack traces/versions**: generic errors to clients, details to logs only.
- **Secrets in the frontend bundle** (`VITE_`/`NEXT_PUBLIC_` API keys): anything shipped to the browser is public — proxy through your backend.
