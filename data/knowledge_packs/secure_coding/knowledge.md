# Secure Coding

## Input validation
- **Never trust input**: body, query, headers, cookies, file names, file contents, URLs, webhook payloads. Client-side checks are UX only — revalidate server-side.
- Validate type/length/range/format with a schema (zod, pydantic, JSON Schema) at the boundary; **allowlist, don't blocklist** (enumerate what's valid, not what's evil).
- Canonicalize before validating (decode %-encoding, normalize unicode/case) so checks can't be bypassed by encoding tricks.
- Reject, don't "clean": sanitizing bad input in place invites bypasses; fail closed with a 400/422.

## Injection
- **SQL**: parameterized queries/prepared statements only — `db.query("SELECT * FROM t WHERE id = $1", [id])`. Never string-build SQL, including `ORDER BY`/table names (those need an allowlist map, params can't cover identifiers).
- **Command**: avoid the shell; pass argv arrays — `execFile("convert", [src, dst])`, Python `subprocess.run([...], shell=False)`. Never interpolate user input into a shell string.
- **Path traversal**: resolve then verify containment — `p = path.resolve(base, name); if (!p.startsWith(base + path.sep)) reject`. Reject `..`, absolute paths, null bytes; serve by ID lookup, not user-supplied filename.
- **XSS**: encode for the output context. DOM: `el.textContent = x`, never `innerHTML` with untrusted data; templates with auto-escaping on; sanitize rich HTML with DOMPurify — never a homemade regex. Add a Content-Security-Policy as backstop.
- **NoSQL/ORM injection**: reject operator objects in user input (`{"$gt":""}` in Mongo filters) — schema-validate to primitives first.
- **Template/eval injection**: never `eval`/`Function`/template-render user-controlled strings.

## AuthN / AuthZ
- Authenticate, then **authorize on every request, on every object**: `/orders/42` must verify order 42 belongs to the caller (IDOR/broken object-level auth is the most common real-world API hole). Deny by default; centralize checks in middleware/policy layer, not scattered `if`s.
- Passwords: **argon2id or bcrypt** (cost ≥ 12) — never plaintext, MD5, SHA-1, or unsalted/fast SHA-256. Rate-limit login + lockout/backoff; constant-time comparison for secrets (`crypto.timingSafeEqual`).
- Sessions: httpOnly + Secure + `SameSite=Lax`(or Strict) cookies; regenerate session ID on login (session fixation); server-side invalidation on logout.
- **CSRF**: needed for cookie-based auth on state-changing requests — SameSite cookies + anti-CSRF token; pure Bearer-token APIs don't need it (no ambient credential).
- JWT: verify signature **and** `alg` (reject `none`), `exp`, `aud`, `iss`; short-lived access tokens; don't put secrets/PII in claims (payload is only base64); revocation needs a server-side list or short expiry + refresh.
- Least privilege everywhere: DB user without DDL, tokens scoped narrowly, no root containers.

## Secrets
- Secrets live in env/secret manager — **never** in code, git history, client bundles, logs, or error messages. A secret that ever hit git is burned: rotate it, don't just delete the commit.
- Prefix keys (`sk_live_...`) so scanners catch leaks; run gitleaks/trufflehog in CI; `.env` in `.gitignore` from commit zero.
- Scrub secrets/PII from logs and crash reports (redaction filters); never log full request headers or bodies wholesale.

## Crypto do / don't
- **Hash vs encrypt**: passwords are *hashed* (one-way, argon2id/bcrypt/scrypt), never encrypted. Data you must read back is *encrypted* (AES-256-GCM — authenticated encryption; never ECB, never CBC without a MAC).
- Random: CSPRNG only for tokens/IDs — `crypto.randomBytes`/`crypto.randomUUID`, Python `secrets` — never `Math.random()`/`random` for anything security-relevant.
- Unique IV/nonce per encryption (GCM nonce reuse = catastrophic); keys from a KDF (HKDF/argon2), not raw passwords.
- Never roll your own crypto or protocol — use libsodium/WebCrypto/vetted libs. HMAC-SHA256 for integrity/signing (webhooks); compare MACs constant-time.
- TLS everywhere, verify certs (never ship `rejectUnauthorized: false` / `verify=False`), HSTS on.

## SSRF & outbound requests
- Any feature that fetches a user-supplied URL (webhooks, importers, previews) can be aimed at internal targets: `http://169.254.169.254/` (cloud metadata), `localhost`, RFC1918 ranges.
- Fix: allowlist schemes (https only) + destination hosts; resolve DNS and reject private/link-local/loopback IPs **at connect time** (DNS rebinding defense); no redirects-follow into private space; egress-restrict the fetching service.

## Dependencies & supply chain
- Pin versions with a lockfile; audit (`npm audit`, `pip-audit`, `osv-scanner`) in CI; patch fast on critical CVEs.
- Beware typosquats and install scripts (`--ignore-scripts` where viable); minimize dependency count; watch for hijacked maintainers on updates — review diffs of small critical deps.
- Don't deserialize untrusted data with native deserializers (Python `pickle`, Java serialization, PHP `unserialize`, YAML `load`) — JSON + schema validation only.

## Mass assignment & logic flaws
- Never bind request bodies straight to models (`User.update(req.body)`) — attacker adds `"role":"admin"`, `"balance":0`. Fix: explicit field pick/DTO schema per endpoint (`{name, email} = validated`).
- Race conditions on money/limits (double-spend via parallel requests): enforce invariants in the DB — unique constraints, `UPDATE ... WHERE balance >= ?` conditional writes, row locks/serializable transactions — not read-then-write in app code.
- Server must recompute prices/totals/permissions — never trust client-sent amounts, roles, or feature flags.

## Defense hygiene
- Errors: full detail to server logs, generic message + request ID to client — no stack traces, SQL, paths, versions.
- File uploads: validate type by content (magic bytes), cap size, randomize stored name, store outside web root / in object storage, never execute.
- Security headers: CSP, `X-Content-Type-Options: nosniff`, `frame-ancestors`/`X-Frame-Options`, HSTS. Open redirects: allowlist redirect targets — never `res.redirect(req.query.next)` raw.
- Fail closed; secure defaults; log auth events (login, failures, privilege changes) for detection.

## Gotchas -> Fix
- **String-built SQL "just this once"** (dynamic ORDER BY, IN-lists) → allowlist identifiers; expand placeholders for IN.
- **Validated on the client only** → server-side schema validation on every endpoint.
- **IDOR**: authenticated user reads others' objects by ID → object-ownership check in a central authorization layer; test with two accounts.
- **`Math.random()` session/reset tokens** → CSPRNG (`crypto.randomBytes(32).toString('hex')`).
- **Password reset token leaks via referrer/logs** → single-use, short-lived, hashed at rest, POST-only consumption.
- **JWT `alg: none` / key confusion** → pin the algorithm server-side; verify with the right key type.
- **`innerHTML` with user data** → `textContent`, or DOMPurify for rich text; CSP as backstop.
- **Secrets committed to git** → rotate immediately; add secret scanning to CI; history rewrite alone is not remediation.
- **SSRF via "fetch this URL" feature** → scheme+host allowlist, private-IP block after DNS resolution, no auto-redirect.
- **`pickle.loads`/`yaml.load` on user data = RCE** → JSON + schema; `yaml.safe_load`.
- **Timing leak comparing secrets with `===`** → `timingSafeEqual`/`hmac.compare_digest`.
- **Verbose 500s leaking internals** → generic client error + request ID; details only in logs.
- **CORS `*` with credentials / reflected origin** → explicit origin allowlist.
- **Unlimited login attempts** → rate limit + progressive backoff + credential-stuffing detection.
