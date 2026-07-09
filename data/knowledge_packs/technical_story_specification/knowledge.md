# Technical Story Specification

## What this layer is
- The engineering detail that turns a user story + acceptance criteria into something a dev can build without re-deriving unknowns. Lives on the story (or a linked design note), NOT in the user's head.
- Rule of thumb for **how much**: specify **interfaces + constraints + contracts**, not line-by-line implementation. Enough that two engineers would build compatible things; not so much you've written the code in prose.
- Include: affected components/**file paths**, API contracts, data model + migrations, UI states, integration points/dependencies, NFRs, chosen approach + rejected alternatives, risks/spikes, explicit out-of-scope, test/verification plan.
- Interface-first: pin the **boundaries** (endpoint signatures, schemas, events, function/module contracts) before internals. Boundaries are what other people/stories depend on; internals stay negotiable.
- Depth scales with risk/coupling: a CRUD field add needs a paragraph; a new payment integration needs contracts + migration + rollback + NFRs.

## Affected components / file paths
- Name the concrete surface, not "the backend". `services/orders/api/routes/checkout.py`, `web/src/features/cart/CartSummary.tsx`, `db/migrations/`, `packages/shared/types/order.ts`.
- List **new** vs **modified** vs **deleted**. Flag shared/hot files (touched by many teams) — coordination risk.
- Call out cross-repo/cross-service touches explicitly; they usually mean a dependency or a split.

## How much detail — decision guide
- **More detail when**: crosses a service/team boundary; changes a persisted schema; new external integration; security/money/PII touched; concurrency or ordering matters; consumed by code you don't own. These are promises others build on — pin them hard.
- **Less detail when**: internal to one module; easily reversible; well-trodden pattern the team knows; UI-only tweak. Over-specifying these wastes time and insults the implementer.
- Signal you've over-specified: you named local variables, chose a loop style, wrote pseudo-code the compiler could reject. Signal you've under-specified: a reviewer/dev has to DM you to know the response shape, the error case, or the deploy order.
- Prefer **declarative artifacts over prose**: an OpenAPI stub, a SQL DDL, a TypeScript type, a JSON example — they're precise and reviewable. Prose describing a schema always drifts from the schema.
- The story owns the **what/contract**; the PR owns the **how**. Keep them in their lanes so the story stays stable while implementation evolves.

## API contracts
- Specify each endpoint: method + path, auth/scope, request schema, response schema (success + error shapes), status codes, idempotency, pagination, versioning.
- For **event/async contracts**: topic/queue name, message schema, delivery guarantee (at-least-once/exactly-once), ordering, partition key, consumer group, poison/DLQ handling. An event is an API — spec it like one.
- **Versioning/back-compat**: is this additive (safe) or breaking? Additive fields default-safe; breaking needs a version bump or dual-read window. State the compatibility contract so consumers aren't surprised.
- **Contract test** the boundary: schema validation / consumer-driven contract (Pact) / generated types so spec and code can't silently diverge.
- Give a concrete example payload, not just field names — examples kill ambiguity.
- Define error contract: shape, codes, which cases (`404` vs `409` vs `422`). "Update the API" is not a contract.
```
POST /v1/orders/{id}/refund      auth: order:write
Req:  { "amount_cents": 500, "reason": "damaged", "idempotency_key": "uuid" }
200:  { "refund_id": "rf_123", "status": "pending", "amount_cents": 500 }
409:  { "error": "already_refunded", "refund_id": "rf_120" }   // full refund exists
422:  { "error": "amount_exceeds_charge", "max_cents": 500 }
Notes: partial refunds allowed; sum(refunds) <= charge; idempotency_key dedupes 24h.
```

## Data model + migrations
- Schema delta: table/column, type, nullability, default, constraints, indexes. New index on any new query filter/sort/join key.
- **Migration plan is mandatory** for schema change: forward migration, backfill strategy for existing rows, default for new nullable-vs-not, and rollback/rollforward. State expand->migrate->contract if renaming/removing.
- Backfill: batched vs single-shot, online vs maintenance window, how long, idempotent/resumable.
- Data volume + growth so indexes/partitioning are sane.
```
ALTER TABLE orders ADD COLUMN refunded_cents INT NOT NULL DEFAULT 0;
CREATE INDEX CONCURRENTLY idx_orders_status_created ON orders(status, created_at);
Backfill: none needed (default 0). Rollback: DROP COLUMN (safe; no reads until vN+1).
Deploy order: 1) add column, 2) ship writer, 3) ship reader. (expand/contract)
```

## UI specifications
- Enumerate **all states**: default, empty, loading, error, partial, success, disabled, permission-denied. Empty/loading/error are the ones most often dropped.
- Validation: which fields, client vs server, messages, when it fires (blur/submit).
- Link the design/mock (Figma frame + node), responsive breakpoints, a11y (focus order, labels, contrast), i18n/RTL if relevant.
- State copy in the spec: e.g. empty="No refunds yet", error="Couldn't load refunds. Retry.".

## Integration points + dependencies
- External services/APIs, feature flags, config/env vars, secrets, message topics/events consumed or emitted (name + schema + delivery guarantee).
- **Dependencies**: upstream stories/PRs/infra that MUST land first; block or sequence them explicitly. "Depends on #482 (auth scope)".
- Contracts with other teams: who owns the other side, is it agreed, is there a stub/mock available.

## Non-functional requirements (NFRs)
- **Performance budget**: p95 latency target, throughput, payload size, N+1 limits, timeout. "Endpoint p95 < 200ms at 50 rps."
- **Security**: authz rule (who can call), input validation, PII handling, rate limit, audit-log event.
- **Accessibility**: WCAG level, keyboard, screen-reader labels, contrast.
- **Observability**: metrics/counters, log lines with correlation id, trace span, alert threshold, dashboard.
- **Reliability**: idempotency, retry/backoff, timeout, failure mode, rollback.
- Attach NFRs as testable AC where possible so they're verified, not aspirational.

## Technical approach / design notes
- State the **chosen approach** in a few bullets and **why**. Note **rejected alternatives** + reason — prevents relitigating in review and records the trade-off.
- Diagram (sequence/component) when flow crosses >2 services. ASCII or linked image.
- Concurrency, transaction boundaries, consistency model, caching + invalidation, backward compatibility.
```
Approach: emit `order.refunded` event; refund-worker calls PSP async.
Why: PSP call is slow/flaky — keep request path fast, get retries for free.
Rejected: synchronous PSP call in request (blows 200ms budget, no retry).
Rejected: cron poll (adds latency, extra infra). 
Idempotency: idempotency_key -> unique constraint on (order_id, key).
```

## Risks / unknowns / spikes
- List open questions with an owner and a resolution path. Unknown that blocks estimate -> **spike** first (timeboxed), record the **spike outcome** back on the story as decisions/contracts.
- A spike's deliverable is a decision + updated spec, not code. "Spike: can PSP do partial refunds? -> yes, `/refunds` endpoint, 24h window; see contract above."
- Flag assumptions explicitly so they can be challenged.

## Explicit out-of-scope
- Bulleted "NOT in this story": adjacent features, edge cases deferred, platforms excluded. Prevents scope creep and reviewer confusion. e.g. "Out: refund to alternate payment method; multi-currency; UI for admins (separate story #490)."

## Test plan / verification
- How each AC is verified: unit/integration/e2e/manual, key cases incl. negative + boundary, test data/fixtures, environment.
- Verification steps a reviewer/QA can run. Tie to observability (what metric/log confirms it in prod).
- Name the **test data** explicitly (seed rows, factory, fixture file) — "test with a real order" is not runnable. State how to reach the flow (route, feature flag on, role).
- Include a **rollout/verify-in-prod** step for risky changes: canary %, metric to watch, rollback trigger. Verification doesn't end at merge.

## Feasibility & sequencing signals
- If the spec can't be written because a fact is unknown -> that's a **spike**, not a story; the story isn't Ready until the spike resolves it.
- If the spec reveals two independently-valuable slices -> **split** the story; a spec spanning multiple contracts/migrations is usually two stories.
- If affected paths include a file another in-flight story edits -> flag the **merge/sequencing** dependency now, not at rebase time.
- Estimate should reference the spec: contracts + migration + states drive the number. A story sized before its technical shape is known is a guess.

## Well-specified section (template)
```
### Technical Notes — Story #487 Partial Refunds
Components: orders/api/routes/refund.py (new), orders/workers/refund_worker.py (new),
  web/src/features/orders/RefundModal.tsx (new), db/migrations/0142_refunds.sql (new)
API: POST /v1/orders/{id}/refund  (contract above)
Data: table `refunds`(id, order_id FK, amount_cents, reason, status, idempotency_key UNIQUE, created_at);
  idx on (order_id); ALTER orders ADD refunded_cents (above). No backfill.
UI: RefundModal states: form / submitting / success / error(409,422 mapped to copy).
  Figma: order-detail/node-88. Validate amount 1..max_refundable on blur + server.
Integrations: PSP `/refunds` (owned by payments team, agreed); emits `order.refunded`.
NFR: request p95 <150ms (PSP async); authz `order:write`; audit `refund.created`;
  metric `refunds_total{status}`; retry worker 5x exp backoff.
Approach: async via event (above). Rejected: sync PSP call.
Risks: PSP sandbox flaky -> spike #486 done, contract stable.
Out of scope: refunds >charge, multi-currency, admin bulk refund (#490).
Test: unit(amount rules), integration(idempotency dedupe), e2e(happy+409), manual(PSP sandbox).
```

## Pitfalls -> Fix
- **Over-specification** (pseudo-code for every line, naming private vars): brittle, wastes review, removes engineer judgment. Fix: specify interfaces/contracts/constraints; leave internals to the implementer.
- **Missing contracts** ("returns the order data"): consumers guess shape. Fix: exact request/response schema + example + error shape + status codes.
- **Ambiguous "update the API"**: no method/path/fields. Fix: name endpoint, list changed fields, version/back-compat, error cases.
- **No data-migration plan**: schema change with no backfill/rollback/deploy-order. Fix: expand->migrate->contract, batched idempotent backfill, explicit rollback.
- **Missing index**: new filter/sort column, no index -> prod slow query. Fix: add index for every new query predicate; state it in the spec.
- **Hidden coupling**: story silently touches a shared/hot file or another service. Fix: list all affected paths; declare cross-service touches as dependencies.
- **No NFRs**: "make it fast/secure" unquantified. Fix: numeric budgets (p95, rps), explicit authz rule, observability signals, all as testable AC.
- **UI missing empty/loading/error**: only happy state designed. Fix: enumerate every state with copy + validation before build.
- **Undeclared dependencies**: build blocks on an unmerged PR/flag/infra discovered mid-sprint. Fix: list upstream deps and sequence/block them.
- **No rejected-alternatives record**: same debate reopens in PR review. Fix: one line per alternative + why not.
- **Unbounded scope**: reviewer/dev unsure where it ends. Fix: explicit out-of-scope bullets.
- **Spike with no written outcome**: research done, decisions lost. Fix: fold spike results (decisions/contracts) back into the story before it's Ready.
- **Contract drift**: spec says one shape, code ships another. Fix: generate types from schema / contract test; treat schema as source of truth.
- **Spec rots**: notes written once, never updated after decisions change. Fix: update the story when contracts change; it's the shared source of truth, not a one-time artifact.
- **Detail with no interface**: pages of internals, endpoint signature still vague. Fix: pin boundaries first; internals are negotiable, boundaries are the promise.
