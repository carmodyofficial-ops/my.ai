# Microservices Architecture

## Core principles
- A microservice owns one **business capability**, its own data store, and its deploy/release cadence. Independently deployable is the acid test — if you must deploy service A and B together, they are one service.
- Optimize for **team autonomy and independent deployability**, not for small line counts. "Micro" ≠ tiny.
- Each service = one team (Conway's Law: system structure mirrors org communication). Design service boundaries around team boundaries.
- Cost of entry is high: distributed tracing, service discovery, CI/CD per service, network failure handling, data consistency. Only pay it when the org/scale demands it.

## Service boundaries (DDD)
- Draw boundaries at **bounded contexts** (DDD): a context has one consistent model + ubiquitous language. "Customer" in Sales ≠ "Customer" in Billing — different models, different services.
- **Aggregates** define transactional consistency boundaries: one aggregate = one service's local ACID transaction. Cross-aggregate consistency is eventual.
- Prefer boundaries with **high cohesion inside, low coupling across**. If two services constantly change together or chat every request, the boundary is wrong — merge them.
- Decompose by **business subdomain** (Orders, Inventory, Payments), not by technical layer (no "the DAO service", "the UI service").
- Start with a **modular monolith**; extract services along seams that prove stable and independently scalable. Premature decomposition = distributed guesswork.

## Data per service — no shared DB
- Each service owns its schema; **no other service touches its tables**. Shared DB = the #1 anti-pattern (couples deploys, schema changes break everyone, hidden coupling).
- Need another service's data? Call its API or subscribe to its events and keep a **local read replica/projection**. Duplicating data is expected and correct.
- Cross-service queries: API composition (gateway/BFF fans out and joins) or CQRS read model built from events. No cross-service JOINs.
- Reference data (currencies, country codes): replicate or cache locally; don't create a runtime dependency on a "lookup service" for every request.

## Sync vs async communication
- **Sync (REST/gRPC)**: request/response, caller blocks, temporal coupling (callee must be up). Use for queries needing an immediate answer. gRPC for internal high-throughput/typed; REST for broad compatibility.
- **Async (events/messages via broker)**: fire-and-forget or event stream, temporal decoupling, better resilience/scalability. Use for state propagation, workflows, and anything tolerant of eventual consistency.
- Rule of thumb: **commands/queries sync, facts/notifications async**. Prefer async to reduce coupling; each sync hop adds a failure mode and latency.
- Every sync call needs a **timeout**; a chain of N sync calls multiplies latency and failure probability.

## Saga pattern (distributed transactions)
- No 2PC across services — use **sagas**: a sequence of local transactions, each with a **compensating action** to undo on failure. Eventual consistency, not atomicity.
- **Choreography**: services react to each other's events, no central coordinator. Loose coupling; hard to see the overall flow; risk of cyclic event dependencies. Good for simple, few-step flows.
- **Orchestration**: a central orchestrator (state machine) tells each service what to do and handles compensation. Explicit, observable, testable; orchestrator can become a bottleneck/god-service. Good for complex, many-step flows.
- Sagas need **idempotent steps** and **idempotent compensations** (redelivery + retries are inevitable). Compensation may be semantic (refund) not literal (can't un-send an email).

## API gateway & discovery
- **API gateway**: single entry for external clients — routing, auth/TLS termination, rate limiting, request aggregation, protocol translation. Prevents clients from knowing internal topology. Risk: becomes a monolith itself — keep logic thin.
- **BFF (Backend-for-Frontend)**: a gateway per client type (web/mobile) so each gets tailored payloads.
- **Service discovery**: services register (Consul/Eureka/etcd) or use platform DNS (Kubernetes Services). Client-side (client picks instance) vs server-side (LB picks) discovery.
- **Service mesh** (Istio/Linkerd): sidecar proxies handle mTLS, retries, timeouts, circuit breaking, tracing — moves resilience out of app code.

## Resilience patterns
- **Timeout**: bound every remote call. No timeout = threads pile up under a slow dependency.
- **Retry**: only for **idempotent** ops; use exponential backoff + jitter + a cap. Naive retries cause retry storms.
- **Circuit breaker** (closed→open→half-open): after N failures, trip open and fail fast for a cooldown, then probe. Stops cascading failure and gives the dependency room to recover.
- **Bulkhead**: isolate resources (thread pools/connection pools) per dependency so one slow dependency can't exhaust everything.
- **Fallback / graceful degradation**: cached value, default, or partial response instead of a hard error.
- **Load shedding / rate limiting**: reject early when overloaded rather than collapse.

## Observability
- **Distributed tracing** (OpenTelemetry, Jaeger, Zipkin): propagate a **trace/correlation ID** across every hop; without it you cannot debug a request spanning 10 services.
- **Structured logs** with the correlation ID; centralized aggregation (ELK/Loki).
- **Metrics**: RED (Rate, Errors, Duration) per service; USE (Utilization, Saturation, Errors) per resource. Alert on SLOs.
- **Health checks**: liveness (restart if dead) vs readiness (route traffic only when ready).

## Versioning & contracts
- Evolve APIs **backward-compatibly**: add optional fields, never remove/rename/repurpose in place. Break = new version (`/v2`, new topic).
- **Consumer-driven contract tests** (Pact): consumers publish expectations; providers verify against them in CI — catches breaking changes before deploy without full E2E.
- **Tolerant reader**: consumers ignore unknown fields, don't over-validate.
- For events, version the schema (see event-driven pack); support N and N-1 during rollout.

## When NOT to use microservices
- Early-stage startup / small team / unclear domain boundaries → **monolith** (or modular monolith) is faster and cheaper.
- Low scale, single team, tightly-coupled domain → the operational tax outweighs the benefit.
- No CI/CD, no observability, no on-call maturity → you'll build a distributed mess. Earn the infra first.
- If in doubt: **monolith first**, extract services when a specific seam demonstrably needs independent scaling/deploy/team ownership.

## Gotchas -> Fix
- **Distributed monolith** (services deploy together, sync-call each other in lockstep, share a DB) -> re-draw boundaries around bounded contexts; give each its own store; move coupling to async events. You got all the cost and none of the benefit.
- **Shared database** across services -> each service owns its schema; expose data via API/events + local projections.
- **Chatty calls** (N+1 across the network; one user action → dozens of sync hops) -> coarser API operations, batch endpoints, API composition, or push data async so it's local. Network calls are ~1000× a local call.
- **No timeouts / naive retries** -> timeout every call; retry only idempotent ops with backoff+jitter+cap; add circuit breakers.
- **Synchronous chains** (A→B→C→D) -> latency and failure compound; flip steps to async events or orchestrate a saga.
- **Missing correlation IDs** -> unroutable debugging; enforce trace-context propagation via mesh/middleware from day one.
- **Dual-write** (write DB then publish event non-atomically) -> use the **outbox pattern** (write event to an outbox table in the same local transaction; a relay publishes it).
- **Non-idempotent consumers/saga steps** -> dedupe by message id; make compensations safe to re-run.
- **Nano-services** (one service per class/table) -> excessive network hops and ops overhead; consolidate to capability-sized services.
- **Entity services** ("Customer service" that only CRUDs a table) -> anemic, chatty; model around behavior/capability, not data entities.
- **Versioning by mutation** (changing a field's meaning) -> additive changes only; new version for breaking changes; contract tests in CI.
- **Orchestrator becomes a god-service** -> keep orchestration to workflow coordination; business rules stay in the owning services.
- **Skipping the monolith** -> premature decomposition freezes wrong boundaries; start monolith/modular-monolith, extract on proven seams.
