# Networking & Security Reference

## Models & Transport
- **OSI 7**: 1 physical, 2 data-link (MAC, Ethernet, switch), 3 network (IP, routing), 4 transport (TCP/UDP), 5-6 session/presentation (TLS), 7 application (HTTP/DNS). **TCP/IP 4**: link, internet, transport, application. "L7 proxy", "L4 LB" reference these.
- **IP+port** = address+door; `1.2.3.4:443`. Port picks the process; <1024 privileged. **TCP** = ordered, reliable, connection (3-way handshake SYN/SYN-ACK/ACK), flow+congestion control — HTTP, SSH, DB. **UDP** = connectionless, no retransmit/ordering, low latency — DNS, video, VoIP, QUIC. TCP teardown FIN/ACK leaves sockets in `TIME_WAIT` (normal).

## DNS
- Resolution: stub → recursive resolver → root → TLD → authoritative → **A** (IPv4)/**AAAA** (IPv6). Records: `CNAME` alias, `MX` mail, `TXT` (SPF/DKIM/verification), `NS`, `PTR` reverse, `SOA`. **TTL** caches results — low TTL before a migration. Test: `dig +short example.com`, `dig @8.8.8.8 x MX`, `dig +trace`.
- DNS is UDP/53 (TCP/53 for large/zone-transfer). DoH/DoT encrypt queries.

## HTTP / HTTPS
- Methods: GET(read, idempotent) POST(create) PUT(replace, idempotent) PATCH(partial) DELETE HEAD OPTIONS(CORS preflight). REST: noun URLs, verb = method.
- Status: **2xx** ok (200, 201, 204), **3xx** redirect (301 perm, 302 temp, 304 not-modified), **4xx** client (400 bad, 401 unauthenticated, 403 forbidden, 404, 409 conflict, 429 rate-limit), **5xx** server (500, 502 bad-gateway, 503 unavailable, 504 timeout).
- Headers: `Content-Type`, `Authorization: Bearer …`, `Set-Cookie` (`HttpOnly` `Secure` `SameSite`), `Cache-Control`, `X-Forwarded-For`/`-Proto` (real client behind proxy). HTTP/2 multiplexes; HTTP/3 = QUIC over UDP.

## TLS / Certificates
- Provides encryption + integrity + **server identity**. Handshake: ClientHello (ciphers/SNI) → cert → key exchange (ECDHE = forward secrecy) → symmetric session key. TLS 1.2/1.3 only; **disable SSLv3/TLS1.0/1.1**.
- Cert (X.509) signed by **CA**, binds domain→pubkey; client verifies chain to a trusted root + expiry + hostname (SAN, not legacy CN). Chain = leaf → intermediate(s) → root; server must send intermediates or clients fail. mTLS = both sides present certs. Let's Encrypt/ACME auto-renew (90-day). HTTPS = HTTP over TLS on 443.

## Addressing, Subnets, NAT
- `127.0.0.1`/localhost = this host only. Private (RFC1918): `10.0.0.0/8`, `172.16/12`, `192.168/16`. Public = routable. Bind `0.0.0.0` to expose beyond localhost, `127.0.0.1` to keep local.
- **CIDR**: `/24` = 256 addrs (254 usable), `/16` = 65k, `/32` = one host. Mask bits = network prefix; rest = hosts. Split into subnets per tier (public/private/db).
- **NAT**: many private hosts share one public IP (source-NAT outbound); inbound needs explicit **port-forward**/DNAT + firewall allow. Breaks unsolicited inbound (why VPN/hole-punch exists).

## Firewalls, Proxies, LB, VPN
- Firewall filters by src/dst IP+port+proto; **default-deny** inbound, allow-list needed ports. `ufw allow 443/tcp`, `iptables`/`nftables`, cloud security groups (stateful — return traffic auto-allowed). Egress filtering limits exfil/SSRF.
- **Forward proxy** = client-side (egress control, caching). **Reverse proxy** (nginx, Envoy, HAProxy) = server-side: TLS termination, route `/api`→app, compression, WAF, **load-balance**.
- **LB algorithms**: round-robin, least-conn, IP-hash (sticky). L4 (TCP, fast, opaque) vs L7 (HTTP-aware routing). Health checks pull dead backends. Add `X-Forwarded-For` so app sees real client.
- **VPN** = encrypted tunnel into a private network (WireGuard, IPsec, OpenVPN); zero-trust/mTLS increasingly replaces flat VPN trust.

## Security Principles
- **Least privilege**: minimal perms/scopes/roles; scope tokens, short-lived creds. **Defense in depth**: layered controls, no single point.
- **Authn** (who you are — password/MFA/OIDC) vs **authz** (what you may do — RBAC/ABAC); check **both every request**, server-side. Sessions: rotate on login, expire, invalidate on logout.
- **Encryption in transit** (TLS everywhere incl. internal) + **at rest** (disk/DB/backups, KMS-managed keys). **Never trust client input**: validate/sanitize/allow-list server-side; client checks are UX only.
- **Secrets**: env/vault, never in code/logs/git; rotate if leaked. Passwords → **bcrypt/argon2/scrypt** + per-user salt, never MD5/SHA1/plaintext. Use vetted crypto libs, never roll your own.

## OWASP-Aware Defenses
- **Injection (SQL/cmd)**: parameterize `db.execute("…WHERE id=?", [id])`, never string-concat; avoid shelling out with user input.
- **XSS**: `el.textContent` not `innerHTML`; escape on output; CSP header. **CSRF**: SameSite cookies + anti-CSRF token.
- **SSRF**: allow-list outbound URLs, block link-local `169.254.169.254` (cloud metadata). **Path traversal**: reject `..`, canonicalize, chroot.
- **Broken access control** (#1 risk): enforce authz server-side, deny by default, no IDOR (verify object ownership). Rate-limit + lockout + MFA vs brute force. Security headers: `HSTS`, `X-Content-Type-Options: nosniff`, `CSP`.

## Load Balancing & Scaling Detail
- **Sticky sessions** (IP-hash/cookie) needed for stateful backends; prefer stateless + shared session store (Redis) so any node serves any request. Drain connections before removing a backend (graceful shutdown).
- **Timeouts + retries + circuit breakers** at every hop; retries need idempotency + backoff+jitter or they amplify outages. Anycast/GeoDNS + CDN push static content to edge, cut latency + origin load.
- **Rate limiting** (token bucket) per client/IP/key protects backends + mitigates abuse/DDoS. WAF filters L7 attacks (injection, bad bots).

## Common Ports
- 22 SSH, 25/465/587 SMTP, 53 DNS, 80 HTTP, 110/995 POP3, 143/993 IMAP, 443 HTTPS, 3306 MySQL, 5432 Postgres, 6379 Redis, 27017 Mongo, 3389 RDP, 8080 alt-HTTP. Never expose DB/Redis/admin ports to `0.0.0.0`.

## Debug Toolkit
`curl -v https://x` (`-I` headers, `--resolve` bypass DNS) · `dig`/`nslookup` · `ss -tlnp` (listening ports+PID) · `nc -zv host 443` (port open?) · `ping` (ICMP up?) · `traceroute`/`mtr` (path/loss) · `openssl s_client -connect host:443 -servername host` (cert/chain/TLS) · `tcpdump -ni any port 443` · `nmap -p- host` (open ports).

## Gotchas → Fix
- **Unexpected open port** → `ss -tlnp` find owner, close/firewall; default-deny inbound. Bound to `0.0.0.0` unintentionally → bind `127.0.0.1`.
- **Plaintext protocols** (HTTP, FTP, Telnet, unencrypted SMTP) → HTTPS/SFTP/SSH; enforce HSTS + redirect 80→443.
- **Weak/expired TLS** → disable TLS<1.2, weak ciphers/RC4/3DES; monitor expiry (auto-renew ACME). **Cert errors**: missing intermediate chain, hostname/SAN mismatch, clock skew, self-signed not trusted.
- **DNS issues**: stale cache (lower TTL pre-change, flush resolver), propagation delay, wrong record/`NXDOMAIN`, split-horizon; verify with `dig @authoritative`.
- **MTU/fragmentation**: hangs on large payloads over VPN/tunnels (ICMP "frag needed" blocked = PMTUD blackhole) → lower MTU / clamp MSS.
- **Firewall misconfig**: stateful SG needs only inbound rule (return auto-allowed); overly broad `0.0.0.0/0` on SSH/DB → restrict source CIDR. Silent drop vs reject: `nc`/timeout to distinguish.
- **Trusting client input** (hidden fields, JS validation, headers, JWT `alg:none`) → re-validate + verify signatures server-side.
- **CORS**: browser blocks cross-origin JS reads by default — fix is **server** `Access-Control-Allow-Origin`, never a client hack; not a security boundary (server authz still required).
- **Ports vs connectivity**: `ping` ok but app down → check the *port* (`nc -zv`) and the process (`ss`), not just ICMP.
- **Secrets leaked in logs/URLs/git** → rotate, scrub, move to vault; tokens in query strings hit logs/proxies — use headers.
