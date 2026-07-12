# Design Patterns & Architecture

Pick the pattern that FITS the problem, not the fanciest. A pattern is a named tradeoff, not a goal.

## SOLID
- **S**RP: one reason to change per module — split by axis of change, not by noun.
- **O**CP: extend behavior without editing existing code (plug in via interface/strategy).
- **L**SP: subtypes must honor the base contract — no strengthened preconditions or thrown "unsupported."
- **I**SP: small focused interfaces; clients don't depend on methods they don't use.
- **D**IP: depend on abstractions; inject deps; high-level policy doesn't import low-level detail.

## Core principles
- **Composition over inheritance**: has-a beats is-a; inherit only for true subtypes with a stable contract. Deep hierarchies are fragile.
- **Dependency injection**: pass collaborators in (constructor/param); don't `new` them inside — decouples, enables test doubles. DI container is optional sugar.
- **Separation of concerns**: keep IO, business logic, and state apart (pure core, effects at edges).
- **DRY** knowingly — but **rule of three**: don't abstract until the 3rd duplication; a wrong abstraction costs more than duplication (coupling drifts). **KISS**, **YAGNI**: solve today's problem.
- **Law of Demeter**: talk to friends, not strangers (`a.b.c.d` = coupling leak).

## GoF — the useful subset
- **Strategy**: swap algorithms at runtime. `sort(data, key=cmp)`. Replaces `if/else` on type.
- **Factory / Abstract Factory**: decouple creation from use. `make_parser(fmt)`.
- **Observer**: pub/sub events. `bus.on("save", handler)`. Watch listener leaks + ordering.
- **Decorator**: wrap to add behavior, same interface. `@retry @cache def f()`. Composable cross-cutting concerns.
- **Adapter**: bridge incompatible APIs. `StripeAdapter(PaymentPort)`.
- **Facade**: one simple entry over a messy subsystem.
- **Command**: action as object -> queue/undo/log/retry. `cmd.execute()`.
- **Builder**: stepwise construction of complex objects. `Query().where().build()`.
- **Template method**: fixed skeleton, overridable steps (inheritance form of Strategy).
- **Singleton**: rare; prefer DI-scoped instance. Hidden global = test pain, concurrency traps, lifecycle bugs.

## Architecture styles
- **Layered (n-tier)**: UI -> service -> data. Simple, familiar; can drift to anemic + rigid.
- **Hexagonal (ports & adapters) / Clean / Onion**: domain core depends on nothing; IO (DB, HTTP, queue) plugs in at edges via ports. Highly testable; more boilerplate.
- **Event-driven**: components emit/consume events; async, decoupled, scalable. Harder to trace/debug; needs idempotent consumers + observability.
- **CQRS**: separate read model from write model. Only when read/write shapes or loads genuinely diverge; adds sync complexity. Often paired with **event sourcing** (state = append-only event log; rebuildable, auditable, but versioning + snapshots are hard).
- **Monolith vs microservices**: **start monolith** (modular monolith); split for independent scaling/deploy/team boundaries, not fashion. Microservices buy autonomy at the cost of network latency, partial failure, distributed transactions, ops/observability overhead. Split along bounded contexts, not layers.
- **Saga** for cross-service transactions: local txns + compensating actions (no 2PC); orchestrated or choreographed.

## More GoF & structural
- **Iterator**: sequential access without exposing internals (`for x in coll`).
- **State**: object changes behavior with internal state -> replaces sprawling `switch` on a status field.
- **Chain of responsibility**: pass a request along handlers until one handles it (middleware pipelines).
- **Proxy**: stand-in controlling access — lazy load, caching, remote, access control.
- **Composite**: uniform treatment of leaf + tree (files/folders, UI trees).
- **Flyweight**: share immutable intrinsic state across many objects to save memory.
- **Memento**: capture/restore state for undo without breaking encapsulation.

## Domain-driven design essentials
- **Bounded context**: a model valid within one boundary; different contexts own different meanings of "customer." Microservice boundaries follow bounded contexts.
- **Entity** (identity over time) vs **value object** (immutable, equality by value) vs **aggregate** (consistency boundary, one root, txn scope).
- **Ubiquitous language**: shared terms between code and domain experts. **Repository** abstracts persistence of aggregates.

## Reliability & integration patterns
- **Idempotency**: same request applied twice = same result (idempotency key, upsert, dedupe). Essential under at-least-once delivery + retries.
- **Retry** with **exponential backoff + jitter**; cap attempts; only retry idempotent/transient failures.
- **Circuit breaker**: after N failures, **open** (fail fast, stop hammering a sick dependency), **half-open** to probe, **close** on recovery. Prevents cascading failure + retry storms.
- **Bulkhead**: isolate resource pools so one saturated dependency can't starve others. **Timeout** every remote call. **Rate limit / load shed** at the edge.
- **Outbox pattern**: write DB row + event in one txn, relay async — avoids dual-write inconsistency.

## Messaging & data patterns
- **Point-to-point queue** (one consumer per message, work distribution) vs **pub/sub topic** (fan-out to all subscribers).
- **Competing consumers**: N workers on one queue scale throughput; need idempotent handlers + visibility timeout.
- **Dead-letter queue** for poison messages after max retries. **Backpressure** via bounded queues; shed/reject when full.
- **Consistency spectrum**: strong (linearizable, costly) vs **eventual** (converges, available under partition). **CAP**: under a network partition choose consistency or availability. **PACELC**: else, latency vs consistency.
- **Idempotency + at-least-once** beats exactly-once (which is largely a myth across a network) — design consumers to dedupe.

## Gotchas -> Fix
- **Over-engineering**: indirection/config/abstraction adding no value now -> YAGNI; add layers when a second concrete case appears.
- **Premature abstraction**: framework built for imagined futures -> wait for rule of three; keep it concrete.
- **God object / god service**: one class knows/does everything -> split by responsibility (SRP).
- **Anemic domain model**: data bags + all logic in "service" classes -> move behavior onto the entities that own the data (unless deliberate functional/CRUD style).
- **Deep inheritance** (>2-3 levels) -> flatten; favor composition/strategy.
- **Leaky abstraction**: wrapper exposes internals (SQL through the "repository", HTTP codes through the domain) -> translate at the boundary.
- **Singleton as global mutable state** -> hidden coupling, untestable, race-prone -> DI-scoped instance, pass explicitly.
- **Distributed monolith**: microservices that must deploy together / share a DB -> merge, or fix the coupling (own data per service, async contracts).
- **Chatty services**: N synchronous hops per request -> coarser APIs, batch, or co-locate; fan-out amplifies tail latency.
- **Retry storm without breaker/backoff** -> DDoS your own dependency -> backoff+jitter + circuit breaker + budget.
- **Event ordering / duplicate assumptions** -> consumers must be idempotent + tolerate reordering.
- **Pattern for its own sake**: applying a GoF name where a function/`if` suffices -> delete the ceremony.
- **Shotgun surgery / feature envy**: one change touches many classes, or a method uses another object's data more than its own -> regroup responsibilities toward cohesion.
- **Circular dependencies** between modules/services -> extract a shared abstraction or invert one edge (DIP).
- **Temporal coupling**: methods must be called in a hidden order -> encode order in the type/builder or make it explicit.
- **Exactly-once fantasy** across the network -> at-least-once + idempotent consumers.
