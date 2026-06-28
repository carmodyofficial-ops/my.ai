---
name: security-review
description: "How to review or write code for security: check the high-impact classes first (injection, authz/IDOR, secrets, input validation, output encoding) before style, with concrete fixes."
version: 1.0.0
category: Coding
tags: [security, secure, vulnerability, injection, sql injection, xss, csrf, ssrf, authentication, authorization, idor, secrets, owasp, audit, sanitize]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use when writing or reviewing code that touches untrusted input, auth, data access, secrets, or external requests — anything where a bug becomes a vulnerability.

## Procedure

1. Trace untrusted input (request body/query/headers/cookies/files, fetched content, file contents). Everything from outside is hostile until validated server-side (allowlist type/length/range). Client-side checks are UX only.
2. Check injection at every sink: SQL must be parameterized (never string-built); shell must use arg arrays (no `shell=True`/concatenation); output must be context-encoded (`textContent`, auto-escaping templates — never `innerHTML` with user data).
3. Check authorization on every request, including object-level ownership (IDOR: `/order/42` must verify it belongs to the caller, not just that they're logged in). Deny by default.
4. Check secrets handling: nothing in code/logs/git; from env/vault; passwords hashed with bcrypt/argon2 (never plaintext/MD5); errors return generic messages, full detail logged server-side only.
5. Check outbound + paths: SSRF (allowlist outbound, block internal/metadata IPs), path traversal (canonicalize, reject `..`), open redirect (allowlist targets), unsafe deserialization (no pickle of untrusted data).
6. Report by severity: injection / authz / secrets first (high), then resource/error handling, then style. Each finding: where, why exploitable, the concrete fix.

## Pitfalls

- Leading with style nits while an injection or missing-authz bug goes unmentioned.
- Trusting client-side validation or hidden fields.
- Rolling your own crypto instead of a vetted library.
- Verbose errors leaking stack traces / SQL / internal paths to the client.
- Assuming "internal" endpoints are safe (defense in depth).

## Verification

- Every untrusted input is validated server-side; every SQL/shell sink is parameterized; every output is encoded.
- Authz (incl. object ownership) is checked on each request; no secrets in code/logs.
- Findings are ordered by real severity with concrete fixes.
