# Web Security (Advanced)

## CSP Level 3
- **Nonce**: server generates fresh random per response, `Content-Security-Policy: script-src 'nonce-r4nd0m'`, echo on `<script nonce="r4nd0m">`. Nonce MUST be unpredictable (CSPRNG, ≥128-bit) and unique per response — reused/guessable nonce = bypass.
- **Hash**: `'sha256-<base64>'` of exact inline script body; good for static inline, brittle (any byte change breaks it).
- **`strict-dynamic`**: trust propagates from a nonced/hashed script to scripts *it* creates via `document.createElement`, ignoring host allowlists. This defeats allowlist-bypass attacks (see below) — the modern recommended base: `script-src 'nonce-x' 'strict-dynamic' 'unsafe-inline' https: http:` (last tokens are ignored by CSP3 browsers, act as fallback for CSP1/2).
- **Common bypasses**: (1) host-allowlist with a JSONP endpoint or hosting an open `angular`/AngularJS on the allowed origin → arbitrary exec; (2) `'unsafe-eval'` + a template/gadget library; (3) allowing a CDN that serves user content or old vulnerable libs. Allowlists are broadly bypassable — prefer nonce + `strict-dynamic`.
- `object-src 'none'`, `base-uri 'none'` (stops `<base>` hijack of relative script URLs) are mandatory; `require-trusted-types-for 'script'` to enforce Trusted Types.
- Report via `Content-Security-Policy-Report-Only` + `report-to`/`report-uri` before enforcing.

## Trusted Types (DOM XSS)
- `Content-Security-Policy: require-trusted-types-for 'script'` makes dangerous **sinks** throw on raw strings: `innerHTML`, `outerHTML`, `Element.insertAdjacentHTML`, `document.write`, `<script>.src`, `eval`, `setTimeout(string)`, `DOMParser`... Assignment now requires a `TrustedHTML`/`TrustedScript`/`TrustedScriptURL` object.
- Create via a policy: `trustedTypes.createPolicy('app', { createHTML: s => DOMPurify.sanitize(s) })`. Lock which policies can exist with `trusted-types app 'allow-duplicates'`; use `default` policy sparingly (catches stringifications everywhere, easy to over-permit).
- Value: forces every sink through a single audited chokepoint — removes the "find all sinks" problem.

## SRI
- `<script src=cdn integrity="sha384-..." crossorigin="anonymous">` — browser rejects if hash mismatches. Requires CORS on the resource. Doesn't protect against a *versioned* URL changing (pin exact version + hash); breaks silently if CDN recompresses/rewrites bytes.

## CORS deep
- **Preflight** (`OPTIONS`) triggered by non-simple method, custom headers, or non-simple content-type. Server must answer `Access-Control-Allow-Methods/Headers/Origin` + `Max-Age`. Response to the *actual* request also needs ACAO.
- **Credentials**: `Access-Control-Allow-Credentials: true` **cannot** combine with `ACAO: *` — must reflect a specific validated origin. Fetch needs `credentials:'include'`.
- **Misconfig**: reflecting `Origin` blindly + `Allow-Credentials: true` = any site reads authed responses. Also `null` origin trust (sandboxed iframe/data URI can send `Origin: null`). Validate against an allowlist, exact-match, never `startsWith`/regex-suffix (`evil-yoursite.com`).
- CORS controls *who can read cross-origin*; it does NOT stop the request being *sent* (CSRF is separate).

## Cookies
- **`SameSite`**: `Lax` (default in modern browsers) sends on top-level GET navigations only; `Strict` never cross-site (breaks inbound links to authed pages); `None` requires `Secure`. `Lax` still allows top-level GET → not full CSRF protection for state-changing GETs (don't mutate on GET).
- **`__Host-`** prefix: forces `Secure`, `Path=/`, **no `Domain`** → locks cookie to exact host, blocks subdomain injection. `__Secure-` weaker (just requires Secure).
- **CHIPS / `Partitioned`**: cookie double-keyed by top-level site → third-party cookie usable but isolated per embedding site (survives third-party cookie deprecation for legit embeds).
- Always `HttpOnly` (no JS read) + `Secure` for session cookies.

## Clickjacking
- `Content-Security-Policy: frame-ancestors 'self' https://trusted` — replaces legacy `X-Frame-Options`; frame-ancestors wins where both present in modern browsers. `XFO` has no allowlist for multiple origins — use CSP.

## Prototype pollution + DOM clobbering
- **Prototype pollution**: attacker sets `__proto__`/`constructor.prototype` via unsafe merge/`set`/query-parse → poisons all objects (`{}.isAdmin` becomes true, gadget → RCE/XSS). Fix: reject `__proto__`/`constructor`/`prototype` keys, use `Object.create(null)` maps or `Map`, `Object.freeze(Object.prototype)`, avoid deep-merge on untrusted JSON, use `--disable-proto=throw` (Node).
- **DOM clobbering**: injected `<a id="x">`/`<form name="config">` makes `window.x`/`document.config` resolve to elements, overriding expected globals/config lookups → logic bypass or XSS gadget. Fix: don't read config from named DOM refs; Trusted Types + sanitizer that strips `id`/`name` on untrusted HTML.

## Supply chain
- **Lockfiles** committed + `npm ci`/`--frozen-lockfile` (exact, no drift). **Dependency confusion**: internal package name published to public registry with higher version → installed instead; fix with scoped names, registry scoping (`.npmrc` `@scope:registry=`), or reserve names. **Provenance/attestation**: npm provenance (Sigstore), SLSA, verify signatures. Pin, audit (`npm audit`, `osv-scanner`), minimize transitive surface, review postinstall scripts (`--ignore-scripts`).

## postMessage
- **Always** check `event.origin` against an allowlist AND `event.source` before trusting data; `postMessage(msg, targetOrigin)` set `targetOrigin` to exact origin, never `*` for secrets. Missing origin check = XSS/data leak vector.

## JWT pitfalls
- **`alg` confusion**: attacker sets `alg:none` (accepted → unsigned forged token) or swaps RS256→HS256 signing with the *public* key as HMAC secret. Fix: server enforces exact expected algorithm, reject `none`, never let token choose alg. Also: validate `exp`/`nbf`/`aud`/`iss`, use short expiry + rotation, don't store sensitive data in the (base64, readable) payload, verify `kid` against a fixed key set.

## Secure headers stack
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`; `X-Content-Type-Options: nosniff`; `Referrer-Policy: strict-origin-when-cross-origin`; `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: require-corp` (enables `crossOriginIsolated`, mitigates Spectre/XS-leaks); `Cross-Origin-Resource-Policy: same-origin`; `Permissions-Policy` to disable unused features.

## Sanitization vs encoding
- **Encode** for context: HTML-entity for HTML body, attribute encoding in attrs, JS-string escaping in scripts, URL-encoding in URLs — output encoding prevents injection when inserting text. **Sanitize** (DOMPurify) only when you must render untrusted *HTML*; configure allowed tags/attrs, beware `mXSS` (parser roundtrip mutations) — keep DOMPurify current. Never regex-sanitize HTML.

## Gotchas -> Fix
- **CSP allowlist thought safe** but includes a JSONP/CDN gadget → bypassed -> switch to `nonce` + `strict-dynamic`; drop host allowlists.
- **Nonce reused** across responses or from weak RNG → predictable → bypass -> per-response CSPRNG nonce.
- **ACAO reflects Origin + credentials true** → any origin reads authed data -> exact allowlist match, reject `null`.
- **`SameSite=Lax` assumed CSRF-proof** but GET endpoint mutates state -> never mutate on GET; add CSRF token/double-submit for cross-site POST.
- **RS256→HS256 confusion**: verifier accepts token-chosen alg -> pin algorithm server-side.
- **Deep-merge of user JSON** pollutes prototype → app-wide auth bypass -> block `__proto__`/`constructor` keys, null-proto maps.
- **SRI on non-versioned URL** breaks silently on CDN update, or missing `crossorigin` → resource blocked -> pin version + add crossorigin.
- **`frame-ancestors` set but old `X-Frame-Options: ALLOW-FROM`** relied on (unsupported) -> use CSP frame-ancestors, drop ALLOW-FROM.
- **postMessage handler** trusts data without origin check -> validate `event.origin` allowlist first.
- **DOMPurify with custom config** re-enabling `ALLOW_UNKNOWN_PROTOCOLS`/`javascript:` → XSS -> keep defaults, add Trusted Types default policy.
