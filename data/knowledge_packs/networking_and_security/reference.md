# Networking & Security Reference

## The Model
- **IP+port** = address+door; `1.2.3.4:443`. Port = which process/service. <1024 privileged.
- **TCP** = ordered, reliable, connection (HTTP, SSH). **UDP** = fire-and-forget (DNS, video).

## DNS
`example.com` → resolver → root → TLD → authoritative → A/AAAA record → IP. Test: `dig example.com`.

## HTTP/HTTPS
- Methods: GET(read) POST(create) PUT(replace) PATCH(update) DELETE. REST: noun URLs, verbs = methods.
- Status: **2xx** ok, **3xx** redirect, **4xx** client error (400 bad, 401 unauth, 403 forbidden, 404 missing, 429 rate), **5xx** server.
- Headers: `Content-Type`, `Authorization: Bearer …`, `Set-Cookie`.

## TLS
Encryption + integrity + server identity. Cert (X.509) signed by CA, binds domain→pubkey; browser checks chain+expiry. HTTPS = HTTP over TLS.

## Addressing
`127.0.0.1`/localhost = this host only. `192.168.x`/`10.x` = LAN private. Public = routable. Bind `0.0.0.0` to expose beyond localhost.

## NAT / Firewall / Proxy
Private hosts share one public IP via NAT; inbound needs explicit **port-forward** + firewall allow. **Reverse proxy** (nginx) terminates TLS, routes `/api`→app, load-balances.

## Debug Toolkit
`curl -v https://x` · `dig`/`nslookup x` · `ss -tlnp` (listening ports) · `ping host` · `nc -zv host 443`.

## CORS
Browser blocks cross-origin JS reads by default. Fix is **server** sending `Access-Control-Allow-Origin`, not client hacks.

## Security Rules
- **Never trust client input**: validate/sanitize server-side; client checks are UX only.
- **SQL**: parameterize — `db.execute("…WHERE id=?", [id])`, never string-concat.
- **XSS**: set `el.textContent`, not `innerHTML`; escape on output.
- **Secrets**: env vars/vault, never in code/logs/git; rotate if leaked.
- **Authn** (who) vs **authz** (allowed): check both per request.
- **Crypto**: use libs; passwords → bcrypt/argon2, never MD5/plaintext.
- **Brute force**: rate-limit + lockout + MFA.
- **SSRF**: allowlist outbound URLs. **Path traversal**: reject `..`, canonicalize.
- Least privilege; HTTPS everywhere; deny by default.
