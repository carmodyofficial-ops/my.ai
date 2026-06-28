# Secure Coding Rules

## Input
- NEVER trust input (body, query, headers, cookies, files). Validate type/length/range server-side; allowlist, don't blocklist. Client checks are UX only.

## Injection
- SQL: parameterized queries/prepared statements only. `db.exec("...WHERE id=?",[id])` — never f-string/concat.
- Shell: avoid shell; pass arg arrays `execFile(cmd,[arg])`, no `shell=True`. Never concat user input into a command.
- Output/XSS: encode for context. `el.textContent=x` not `innerHTML`. Auto-escape templates; sanitize HTML with a library, never regex.

## AuthN / AuthZ
- Authenticate, then authorize on EVERY request. Check object-level ownership server-side (prevent IDOR: `/order/42` must verify it's yours).
- Deny by default; explicit allow. Least privilege for tokens/DB/roles.
- Passwords: bcrypt/argon2/scrypt. Never plaintext/MD5/SHA1. Rate-limit + lockout on login.
- Sessions/CSRF: SameSite cookies + anti-CSRF token on state-changing requests.

## Secrets & Crypto
- Secrets in env/vault, never in code/logs/git history. Rotate; scrub from errors. Use vetted libs—never roll your own crypto.

## Network/Resources
- TLS everywhere; HSTS; verify certs.
- SSRF: allowlist outbound hosts; block internal IPs/metadata.
- Path traversal: canonicalize, confine to base dir, reject `..`/absolute paths.
- Open redirect: allowlist redirect targets, no raw user URLs.
- Deserialization: no pickle/native deser of untrusted data; use JSON + schema.

## Hygiene
- Dependencies: pin versions, audit (`npm audit`/`pip-audit`), patch fast.
- Errors: log detail server-side; return generic messages—no stack traces/SQL/paths to clients.
- Secure defaults on by default; fail closed.

## Gotchas
Trusting client validation · string-built SQL/shell · secrets in source · homemade crypto · verbose error leaks · missing object-level authz (IDOR) · unchecked redirects/SSRF.
