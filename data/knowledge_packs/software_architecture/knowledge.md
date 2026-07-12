# Software Architecture

## What architecture is / decides
- Architecture = the set of **significant, hard-to-reverse decisions**: structure, boundaries, dependencies, tech choices, and the qualities they optimize for. It's about trade-offs, not "the best" pattern.
- Driven primarily by **quality attributes (NFRs)**, not features. "Architecturally significant requirements" (ASRs) are the ones that shape structure.
- **First law of software architecture**: everything is a trade-off. Second: *why* beats *how* — capture rationale (ADRs).

## Quality attributes (NFRs)
- Runtime: performance/latency, throughput, scalability, availability, resilience/fault-tolerance, security, consistency.
- Structural: modularity, testability, deployability, maintainability, evolvability, portability.
- Make them **measurable** ("p99 < 200ms at 5k rps", "99.95% monthly"), not vague ("fast", "scalable"). Un-measurable NFRs can't drive design or be verified.
- Attributes **conflict**: consistency vs availability (CAP), performance vs security, simplicity vs flexibility. Architecture = choosing which to favor, explicitly.

## Styles (choose per driving attributes)
- **Layered / n-tier**: presentation → business → persistence → DB. Simple, familiar; risk of "sinkhole" (layers just pass through) and a hidden big ball of mud. Good default for small apps.
- **Hexagonal (Ports & Adapters)**: domain core at center; **ports** = interfaces the core owns; **adapters** = driving (UI, API, tests) and driven (DB, queue, external API) implementations. Swap infra without touching core; excellent testability.
- **Onion / Clean**: concentric layers, **dependencies point inward** toward the domain; outer = frameworks/UI/DB, inner = entities + use-cases. Same principle as hexagonal, more layers named.
- **Modular monolith**: single deployable, strong internal module boundaries (enforced, e.g. by package/module visibility). Most teams' best starting point — monolith simplicity + clean seams to extract later.
- **Microservices**: independently deployable services around business capabilities, each owning its data. Buys independent deploy/scale/team autonomy at the cost of distributed-systems complexity (network, consistency, ops).
- **Event-driven**: components communicate via async events; loose coupling, scalable, resilient; harder to reason about end-to-end flow and consistency.
- **Service-based**: coarse-grained services (a few, not many) sharing a DB — middle ground, avoids fine-grained distribution pain.
- **Pipeline / space-based / microkernel (plugin)**: for stream processing, extreme-scale in-memory, and extensible product platforms respectively.

## The dependency rule
- **Source-code dependencies point inward / toward stable abstractions.** High-level policy must not depend on low-level detail; both depend on abstractions (DIP).
- Domain/use-cases never import framework, ORM, or HTTP types. Cross the boundary with interfaces + DTOs; infra implements domain-owned interfaces.
- Enforce with dependency-checking tools (ArchUnit, dependency-cruiser, import-linter, module systems) in CI — otherwise the rule rots.

## ADRs (Architecture Decision Records)
- Short markdown file per significant decision, versioned **in the repo**, immutable once accepted; supersede rather than edit.
- Fields: **Title, Status** (proposed/accepted/deprecated/superseded), **Context** (forces at play), **Decision**, **Consequences** (good + bad), and alternatives considered.
- Purpose: preserve *why*, onboard newcomers, avoid re-litigating settled calls. Missing ADRs = architectural amnesia.

## C4 model (documentation)
- Four zoom levels, each a diagram:
  1. **Context**: system + users + external systems (whole-system, non-technical audience).
  2. **Container**: deployable/runnable units (apps, services, DBs, SPAs) + tech + comms.
  3. **Component**: components inside one container + responsibilities.
  4. **Code**: class/ER detail (usually generated, often skipped).
- Notation-light, audience-scaled. Pair with a **legend**; keep diagrams-as-code (Structurizr, Mermaid, PlantUML) so they stay current.

## Evolutionary architecture & fitness functions
- Assume the architecture will change; optimize for **evolvability** over up-front perfection.
- **Fitness function**: an automated, objective test that a chosen architectural characteristic still holds — e.g. layer-dependency checks, cyclic-dependency detection, p99 latency budget in CI, coupling metrics, security scans. Run continuously; treat architecture like testable code.

## Trade-off analysis (ATAM-lite)
- Elicit driving quality attributes → capture **scenarios** ("under 10x load, p99 stays < X") → map each candidate decision's effect on each attribute → surface **sensitivity points** (small change, big effect) and **trade-off points** (one decision hits multiple attributes oppositely) → decide + record ADR.
- Make the conflict explicit: pick what you're optimizing and what you're sacrificing.

## Coupling, cohesion, connascence
- **High cohesion, low coupling** — the enduring goal. A module should do one thing; changes should stay local.
- **Afferent coupling (Ca)** = who depends on me; **efferent (Ce)** = who I depend on; **instability I = Ce/(Ca+Ce)** (0 stable ↔ 1 unstable). Stable modules should be abstract (SAP: stable-abstractions principle).
- **Connascence** grades coupling by strength + locality: static (name < type < meaning < position < algorithm) and dynamic (execution order < timing < value < identity). Reduce strength, or keep strong connascence local.
- **Temporal/deployment coupling** (must-deploy-together) is the silent killer that produces distributed monoliths — track it explicitly.

## Deployment & data topology
- Separate **logical** architecture (modules/components) from **physical** (processes, containers, nodes, regions). C4 container/deployment diagrams cover the physical.
- **Database-per-service** for microservices — shared DB = tightest coupling and defeats independent deploy. Cross-service reads via API/events + local read models, not joins.
- **Sidecar / service mesh** (Envoy/Istio/Linkerd): offload cross-cutting concerns (mTLS, retries, timeouts, tracing, traffic shaping) out of app code into the platform.
- **API gateway / BFF** (backend-for-frontend): aggregate/adapt downstream services per client type at the edge.

## Governance
- Architecture governance = making the intended architecture the path of least resistance: enforced fitness functions in CI, dependency rules, ADR review, and a lightweight review forum — not a gatekeeping committee.
- Prefer **guardrails + automated checks** over manual approvals; catch drift where it happens (the pipeline), not months later.

## Tech radar
- Company/team ring assessment of technologies: **Adopt / Trial / Assess / Hold**, across quadrants (languages & frameworks, tools, platforms, techniques). Governs tech choices without a top-down mandate; drives conscious, reviewed adoption.

## When to choose what
- Start **modular monolith**; extract microservices only when a specific module has a proven independent scaling/deploy/team-autonomy need.
- Hexagonal/clean when the domain is rich and long-lived (pairs with DDD); plain layered when it's simple CRUD.
- Event-driven when you need decoupling, fan-out, or async resilience — not for simple request/response.
- Consistency-critical + small team → monolith with strong transactions; global scale + many teams → distributed, accept eventual consistency.

## Cross-cutting concerns
- Logging, auth, tracing, retries, caching, validation cut across modules — isolate them (middleware, decorators, aspects, sidecars) so they don't smear through domain code.
- **Correlation IDs + distributed tracing** (OpenTelemetry) are architectural in distributed systems — design them in, not bolt on.

## Pitfalls -> Fix
- **Big Design Up Front (BDUF)** (fully specify before learning anything) -> decide the last responsible moment; keep decisions reversible; use fitness functions to evolve.
- **Ivory-tower architect** (edicts, no code, no context) -> architects pair with teams, prototype/spike, stay hands-on; decisions travel with rationale (ADRs).
- **Resume-driven development** (choosing tech to pad CVs) -> pick by driving quality attributes; justify in an ADR; use a tech radar to gate adoption.
- **Premature microservices** (distribute a domain you don't yet understand) -> modular monolith first; split along proven seams (bounded contexts) later.
- **Distributed monolith** (services that must deploy together, share a DB, chatty sync calls) -> give each service its own data, async/coarse contracts, independent deploy; if you can't, it should be a monolith.
- **No ADRs** (decisions live in people's heads / chat) -> record every significant decision as an ADR in the repo.
- **Accidental big ball of mud** (layered app with no enforced boundaries) -> enforce module boundaries + dependency rule in CI (ArchUnit/dependency-cruiser).
- **Gold-plating for imagined future scale** (kafka + k8s for 100 users) -> architect for current + next-order-of-magnitude, not fantasy; keep it reversible.
- **NFRs as afterthought** -> capture measurable quality-attribute scenarios up front; verify with fitness functions.
- **Diagrams that rot** (stale Visio nobody trusts) -> diagrams-as-code (C4 + Structurizr/Mermaid) in the repo, reviewed with the code.
- **Framework as architecture** (Rails/Spring conventions = your only structure) -> keep domain independent of the framework; the framework is a driven adapter, not the core.
- **Analysis paralysis** (endless trade-off debate) -> timebox, pick, record the ADR, and move; reversible decisions don't need consensus.
