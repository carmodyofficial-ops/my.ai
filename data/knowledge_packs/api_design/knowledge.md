# API Design Reference

## REST Basics
- Resources = **plural nouns**: `/v1/users`, `/v1/users/42/orders`. Never verbs (`/getUser` is wrong).
- Verbs: `GET` read, `POST` create, `PUT` replace, `PATCH` partial, `DELETE` remove.
- Nest for ownership only (`/users/42/orders`); keep depth <= 2.

## Status Codes
`200` ok · `201` created (+`Location`) · `204` no body · `400` malformed · `401` no/bad auth · `403` authed-but-denied · `404` missing · `409` conflict · `422` valid syntax/bad semantics · `429` rate-limited · `500` server. Never 200 with `{error}`.

## Versioning
`/v1/...` in path (simple) or `Accept: application/vnd.api+json;version=1`. Bump only on breaking changes; add fields = non-breaking.

## Pagination / Filtering
- **Cursor/keyset** > offset (offset drifts, slow at depth): `?limit=20&cursor=abc` -> `{data, next_cursor}`.
- Filter/sort via query: `?status=active&sort=-created_at`.
- Always paginate collections — never return unbounded lists.

## Idempotency
- `GET/PUT/DELETE` idempotent by design; `POST` is not.
- For `POST`, accept `Idempotency-Key: <uuid>`; dedupe & replay stored response.

## Errors (consistent envelope)
```json
{"error":{"code":"invalid_email","message":"...","field":"email"}}
```
Stable machine `code`. Never leak stack traces/SQL/internal IDs.

## Auth & Rate Limits
- `Authorization: Bearer <token>`.
- `429` + `Retry-After: 30` + `X-RateLimit-Remaining`.

## Misc
- Content negotiation: `Accept`/`Content-Type: application/json`.
- HATEOAS lite: include `{"_links":{"next":"..."}}` where useful.
- Schema-first: write **OpenAPI** spec, generate clients/validation.

## GraphQL
- Single `POST /graphql`; typed schema is the contract.
- Client picks fields -> avoids over/under-fetching.
- Batch nested resolvers with **DataLoader** to kill N+1 queries.

## Gotchas
- Breaking changes without a version bump.
- Chatty/over-fetching endpoints (force >1 call per view).
- Verbs in URLs; inconsistent naming (`user_id` vs `userId`).
- Leaking internal errors; unpaginated list endpoints.
