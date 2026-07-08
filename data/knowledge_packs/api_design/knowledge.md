# API Design

## REST resource modeling
- Resources = **plural nouns**: `/v1/users`, `/v1/users/42/orders`. Never verbs — `/getUser` is wrong; the HTTP method is the verb.
- `GET` read (safe, cacheable) · `POST` create/process · `PUT` full replace · `PATCH` partial update · `DELETE` remove. `GET`/`PUT`/`DELETE` are idempotent by contract; `POST` is not.
- Nest only for ownership (`/users/42/orders`), depth ≤ 2; cross-cutting lookups get their own top-level collection (`/orders?user_id=42`).
- Non-CRUD actions: sub-resource or action endpoint as last resort — `POST /orders/42/cancel` or model as state: `PATCH /orders/42 {"status":"cancelled"}`.
- Use opaque public IDs (UUID/ULID/prefixed like `ord_9f2c`) — never expose auto-increment DB ids.
- Consistent naming everywhere: pick `snake_case` or `camelCase` for JSON fields and never mix; kebab-case paths; ISO 8601 UTC timestamps (`2026-07-08T12:00:00Z`); money as integer minor units + currency code.

## Status codes
- `200` ok · `201` created (+ `Location` header) · `202` accepted (async job) · `204` success, no body (DELETE).
- `400` malformed request · `401` missing/invalid auth (+ `WWW-Authenticate`) · `403` authenticated but denied · `404` not found (also for hiding existence) · `405` wrong method · `409` conflict (duplicate, version clash) · `410` gone · `412` precondition failed (ETag) · `422` well-formed but semantically invalid · `429` rate limited (+ `Retry-After`).
- `500` unexpected · `502/503/504` upstream/unavailable/timeout. **Never `200` with `{"error": ...}`** — clients and proxies key off the status code.

## Errors (one envelope, everywhere)
```json
{"error":{"code":"invalid_email","message":"email is not valid","field":"email","request_id":"req_abc123"}}
```
- Stable machine-readable `code` (clients branch on it, not on `message`); human `message`; `field`/`details[]` for validation; `request_id` for support correlation.
- Never leak stack traces, SQL, internal hostnames, or library versions. RFC 9457 `application/problem+json` is the standards-track version of this.

## Pagination / filtering / sorting
- **Cursor/keyset beats offset**: offset pages drift when rows are inserted and get slow at depth. `GET /items?limit=20&cursor=eyJpZCI6NDJ9` → `{"data":[...], "next_cursor":"...", "has_more":true}`.
- Cursors are opaque to clients (base64 of sort keys); tie cursor validity to a stable sort (`created_at,id` tiebreaker).
- Filter/sort via query: `?status=active&sort=-created_at` (leading `-` = desc). Cap `limit` (e.g. max 100). **Every collection endpoint paginates** — no unbounded lists, ever.
- Sparse fields / expansion where payloads are heavy: `?fields=id,name` or `?expand=customer`.

## Idempotency & concurrency
- For `POST` create/charge: accept `Idempotency-Key: <uuid>`; store key → response; replay the stored response on retry (same key + same body); `409`/`422` on same key + different body. Expire keys after ~24h.
- Retries without idempotency = duplicate charges/orders. Design every mutating endpoint to be safely retryable.
- Optimistic concurrency: return `ETag`, require `If-Match` on update, `412 Precondition Failed` on mismatch — prevents lost updates.

## Versioning
- Path versioning is the pragmatic default: `/v1/...`. Header/media-type versioning (`Accept: application/vnd.api+json;version=1`) is purer but harder to route/cache/debug.
- Bump only for **breaking** changes: removing/renaming fields, changing types/semantics, tightening validation. Adding optional fields/endpoints is non-breaking — clients must ignore unknown fields.
- Support N and N-1 with a published deprecation window; send `Deprecation`/`Sunset` headers on old versions.

## Auth patterns
- `Authorization: Bearer <token>` — OAuth2/JWT for user-context; short-lived access token + refresh token; validate signature, `exp`, `aud`, `iss` on every request.
- API keys for server-to-server: prefixed (`sk_live_...`) so scanners find leaks; hash at rest; scope + per-key rate limits; support rotation (two active keys).
- Keys/tokens in headers, **never** in query strings (logged everywhere). 401 = who are you; 403 = you can't do that. Always re-check object-level authorization (tenant/ownership) — IDOR is the #1 API vuln.
- Rate limiting: `429` + `Retry-After: 30` + `X-RateLimit-Limit/Remaining/Reset`; per key/user, not per IP alone.

## Webhooks
- Deliver events as `POST` with a signed payload: HMAC-SHA256 of body in a header (`X-Signature: t=...,v1=...`), timestamp included to block replay (reject if older than ~5 min).
- Receiver must verify signature over the **raw body**, respond `2xx` fast (<5s), and process async — queue the work.
- Sender retries with exponential backoff on non-2xx; receivers must be **idempotent** (dedupe on event `id`). Include `id`, `type`, `created`, and full object (or id + fetch). Document event types; provide a redelivery/replay UI.

## Caching & async work
- `Cache-Control` on GETs: `private, max-age=60` per-user, `public, s-maxage=300` CDN-cacheable, `no-store` for sensitive data. `ETag` + `If-None-Match` → `304` saves bandwidth on polls.
- Long-running operations: return `202 Accepted` + `{"job_id": "..."}`/`Location: /jobs/123`; client polls the job resource (`status: pending|succeeded|failed`, then `result`) — don't hold HTTP connections open for minutes.
- Bulk endpoints (`POST /items:batch`) return per-item results (`207`-style array of `{status, error?}`), not all-or-nothing 500s — unless the operation is transactional by design.

## OpenAPI & workflow habits
- Schema-first: write the OpenAPI 3.x spec, review it like code, then generate server stubs/clients/validators — the spec is the contract.
- One `operationId` per operation; shared components (`$ref`) for error envelope, pagination wrapper; mark required fields; `enum` closed sets; provide `examples`.
- Validate requests **and** responses against the spec in CI/tests to prevent drift. Lint the spec (spectral). Publish docs from it.
- Additive evolution: never repurpose a field; deprecate with `deprecated: true` before removal.

## Gotchas -> Fix
- **200-with-error-body** → status codes carry the outcome; envelope carries detail.
- **Offset pagination drifts/slow** → keyset cursor + stable sort with unique tiebreaker.
- **Non-retryable POST** duplicates work on timeout → `Idempotency-Key` with stored replay.
- **Breaking change shipped silently** (field rename/type change) → version bump + deprecation headers + changelog.
- **Verbs in URLs / mixed naming** (`user_id` vs `userId`) → nouns + one casing convention, linted in the spec.
- **Unbounded collection response** → mandatory pagination with a hard max limit.
- **Chatty API** (client needs 5 calls per screen) → expansion params, batch endpoints, or purpose-built read endpoint.
- **404 vs 403 leaks existence** of other tenants' objects → return 404 for unauthorized object access in multi-tenant APIs.
- **Webhook trusted without verification** → HMAC verify raw body + timestamp check; process idempotently.
- **PUT used for partial update** wipes omitted fields → PATCH for partial; PUT only for full replacement.
- **Timestamps in local time / epoch ambiguity** → ISO 8601 UTC strings everywhere.
- **Spec drift from implementation** → contract tests validating live responses against OpenAPI in CI.
