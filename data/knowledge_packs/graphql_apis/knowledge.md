# GraphQL APIs
## Schema and types
- SDL defines types: `type`, `input`, `interface`, `union`, `enum`, `scalar`. Fields are nullable by default; `!` = non-null. `[T!]!` = non-null list of non-null.
- Three roots: `Query` (read), `Mutation` (write, run serially), `Subscription` (stream over WebSocket/SSE).
- Input types (`input`) for mutation args — object types can't be args.
## Schema design
- Nullability: make a field non-null (`!`) only if it can NEVER be null; over-`!` propagates one failure up the whole branch. Default nullable for anything that can error/be absent. List elements: `[T!]!` (non-null list of non-null) vs `[T]` (both nullable) — pick deliberately.
- `interface` = shared fields across types, query with inline fragments `... on Type`; resolve concrete type via `__resolveType`. `union` = "one of these types", no shared fields (e.g. search results, result-or-error).
- Design around use cases, not DB tables. Prefer specific input types per mutation over one god-input. Nullable enums so new values don't break; never renumber/rename enum members.
## Mutations & optimistic updates
- One mutation = one intent (`publishPost`, not `updatePost{status}`). Return a payload type wrapping the entity + `userErrors[]`, so validation failures aren't transport errors.
- Optimistic UI: client writes an expected result to cache immediately, rolls back on error (Apollo `optimisticResponse`, urql `optimistic`). Requires the mutation to return the full mutated entity with `id` so the real response reconciles.
- Mutations with side effects should return enough to update all affected cache entries (e.g. return the parent connection or `deletedId`).
## Resolvers
- `(parent, args, context, info) => value`. `context` carries auth/user/loaders (per-request). Missing resolver falls back to `parent[fieldName]`.
- Resolvers run top-down, fields in parallel per level; nested resolvers only fire for requested fields.
## N+1 and DataLoader
- N+1: parent list of N items each triggers a child fetch → 1+N queries. Classic: `posts` then `post.author` for each.
- Fix: `DataLoader` batches keys collected in one tick into one `batchFn([ids]) -> values` (order/length must match keys) and caches per-request. Create loaders fresh per request in `context` — never module-global (stale + cross-user leak).
```
const userLoader = new DataLoader(ids => batchGetUsers(ids));
author: (post, _, {userLoader}) => userLoader.load(post.authorId)
```
## Pagination
- Cursor/Relay connections beat offset (stable under inserts). Shape: `edges { node, cursor }`, `pageInfo { hasNextPage, endCursor }`, args `first`/`after`.
- Cursor = opaque encoded position (base64 of id/sort key), not an index. Offset `limit/skip` is fine for small stable sets but drifts + slows on deep pages.
## Errors
- Partial success: `data` + top-level `errors[]`; a null field can coexist with data elsewhere. Non-null field error nulls up to nearest nullable parent.
- Put stable machine codes in `extensions.code` (`UNAUTHENTICATED`, `FORBIDDEN`, `BAD_USER_INPUT`). For expected domain failures, prefer typed union results (`Success | ValidationError`) over throwing.
## Auth
- Authenticate in `context` (verify token → user); authorize in resolvers or field middleware, NOT in the gateway. Enforce per-field/per-object, not just per-query.
- Guard against abuse: query depth limit, cost/complexity analysis, `persisted queries` (allowlist) in prod, disable introspection publicly.
## Query limiting & abuse
- Depth limit: cap nesting (e.g. 7) to stop recursive/cyclic blowups. Complexity/cost: assign each field a cost, sum with multipliers for list `first:` args, reject over a budget before execution.
- Rate-limit by cost, not request count (one query can be huge). Cap `first`/`last` page sizes; require pagination on unbounded lists.
- Persisted queries: client sends a hash; server runs only known documents. APQ (automatic) registers on first miss; a strict allowlist blocks arbitrary queries entirely — best DoS defense in prod. Also shrinks request payloads (GET-cacheable by hash).
## Federation & stitching
- Apollo Federation: subgraphs own types; a gateway composes one supergraph. `@key` marks an entity's identifier; `@external`/`@requires`/`@provides` wire cross-subgraph fields; the gateway resolves references via `__resolveReference`.
- Schema stitching = older manual merge of remote schemas. Prefer federation for multi-team ownership; keep a single graph contract.
## Subscriptions transport
- `graphql-ws` (WebSocket, `graphql-transport-ws` protocol) is the modern default; `subscriptions-transport-ws` is deprecated. SSE (`graphql-sse`) works over plain HTTP — simpler, one-way, survives proxies/load balancers better.
- Back with a real pub/sub (Redis, Kafka) across instances; in-memory `PubSub` only works single-process. Authenticate on the connection init/handshake, and re-check authz per event.
## Caching
- Apollo Client normalizes cache by `__typename` + `id` — always request `id` so entities dedupe/update. `cache.modify`/`writeQuery` for manual updates; `fetchPolicy` (`cache-first` default, `network-only`, `cache-and-network`).
- urql: document cache by default; add Graphcache for normalized. Mutations must return updated entities (with `id`) so the cache patches automatically.
- Server: response caching via `@cacheControl`/persisted queries; per-request DataLoader is the request-scoped cache.
## REST comparison
- Over-fetching (REST returns unused fields) and under-fetching (N round-trips) solved by client selecting exact fields in one request. Cost: harder HTTP caching (single POST endpoint), need cost limiting.
## Gotchas -> Fix
- **N+1 explosion**: nested list resolvers hammer DB. Fix: DataLoader per request; batch + cache.
- **Global DataLoader**: caches across users/requests → stale + data leak. Fix: instantiate in `context` per request.
- **batchFn order mismatch**: DataLoader maps results to keys by position; DB returns unordered → wrong data. Fix: re-map results to key order, fill misses with null.
- **Unbounded queries**: deeply nested/aliased query = DoS. Fix: depth + complexity limits, pagination caps, persisted-query allowlist.
- **Introspection in prod**: leaks schema. Fix: disable public introspection; rely on codegen internally.
- **Mutation returns just `ok:true`**: client cache can't update. Fix: return the mutated entity with `id`.
- **Auth only at gateway**: nested fields bypass checks. Fix: field-level authorization in resolvers.
- **Nullability too strict**: one non-null field error nulls the whole branch. Fix: make error-prone fields nullable; use result unions.
- **Enum/scalar drift**: unhandled new enum value crashes clients. Fix: additive schema changes only; deprecate with `@deprecated`, never remove/rename in place.
- **Subscriptions leak**: sockets not cleaned up. Fix: unsubscribe on disconnect; use pub/sub (Redis) not in-memory for multi-instance.
- **Serial mutations assumed parallel**: top-level mutation fields run sequentially — don't rely on parallelism; batch related writes into one mutation.
- **Deleted entity leaves cache stale**: delete mutation returns `ok:true`. Fix: return `deletedId`; `cache.evict`/`invalidate` it and gc dangling refs.
- **Optimistic update never reconciles**: response lacks `id`/fields. Fix: return the full mutated entity so the normalized cache overwrites the guess.
- **Cost analysis ignores list multipliers**: cheap-looking query fans out via `first: 1000` nesting. Fix: multiply child cost by requested page size; cap `first`.
- **APQ without allowlist in prod**: still executes any registered query = still DoS-able. Fix: strict persisted-query allowlist for public prod traffic.
- **In-memory PubSub across replicas**: subscribers miss events published on another instance. Fix: Redis/Kafka-backed pub/sub.
- **Non-null field wraps a fallible resolver**: an error nulls the whole parent object/branch. Fix: make error-prone fields nullable or return a result union.
- **Error message leaks internals**: stack traces/SQL in `errors`. Fix: mask errors in prod, map to stable `extensions.code`, log the detail server-side.
- **Federation `@key` missing/mismatched**: entity can't be resolved across subgraphs. Fix: consistent `@key` fields + `__resolveReference` returning the keyed object.
- **Interface without `__resolveType`**: server can't pick concrete type. Fix: implement `__resolveType` or ensure `__typename` is derivable.
