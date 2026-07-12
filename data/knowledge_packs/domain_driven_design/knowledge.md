# Domain-Driven Design

## Core idea + when it pays off
- DDD = model the **business domain** in code with a language shared by devs + domain experts; align software boundaries with business boundaries.
- Worth it when the **domain is complex** (rich rules, invariants, evolving policy) and you have access to domain experts. Payoff is managing complexity, not raw speed.
- **Overkill** for CRUD apps, technical/generic subdomains, thin data pipes, or when the "complexity" is purely technical (scale, integration) — reach for other tools there.
- Two halves: **strategic** (boundaries, language, team topology) and **tactical** (in-model building blocks). Strategic matters most; skipping it to grab entities/aggregates is the classic mistake.

## Ubiquitous language
- One rigorous, shared vocabulary per bounded context, used identically in conversation, docs, code (class/method names), and tests. `Policy.lapse()` not `Policy.setStatus(3)`.
- The language is **context-scoped**: "account" in Billing ≠ "account" in Identity. Same word, different model — do not force one shared definition.
- Language drift (experts say X, code says Y) is a design smell → refactor code to match the language, or the language is wrong and needs a workshop.

## Strategic design
- **Domain** = the problem space; **subdomains** partition it:
  - **Core**: your competitive differentiator → invest most, best people, deepest modeling.
  - **Supporting**: needed but not differentiating → build simply/in-house.
  - **Generic**: solved commodity (auth, payments, email) → buy/adopt off-the-shelf.
- **Bounded context (BC)**: an explicit boundary within which a model + its ubiquitous language are consistent. The central DDD pattern. A model term is only valid inside its BC.
- BC ≈ solution-space unit; subdomain ≈ problem-space unit. Aim for 1:1 but reality is many:many.
- **Context map**: documents relationships + integration between BCs and the team politics driving them:
  - **Partnership**: two teams succeed/fail together, coordinate closely.
  - **Shared Kernel**: shared subset of model/code; high coupling, needs joint ownership.
  - **Customer/Supplier**: upstream serves downstream's needs; downstream has a voice.
  - **Conformist**: downstream adopts upstream's model wholesale (no leverage).
  - **Anti-Corruption Layer (ACL)**: downstream translates upstream's model into its own — insulates from legacy/vendor/foreign models. Default when integrating with anything you don't control.
  - **Open Host Service / Published Language**: upstream offers a stable, documented protocol (e.g. a well-versioned API/event schema) for many consumers.
  - **Separate Ways**: integration not worth it; duplicate instead.

## Tactical building blocks
- **Value Object**: no identity, defined by its attributes, **immutable**, side-effect-free, self-validating. `Money`, `DateRange`, `Address`. Prefer VOs over primitives (fight "primitive obsession"). Equality by value.
- **Entity**: has a stable **identity** (id) that persists through attribute changes; equality by id, not attributes. Mutable through behavior.
- **Aggregate**: a cluster of entities + VOs treated as one **consistency + transaction boundary**. Has one **aggregate root** (an entity) — the only member referenced from outside.
- **Aggregate root** rules:
  - Outsiders reference only the root; inner entities are reached through it.
  - Root enforces all **invariants** for the whole aggregate; nothing bypasses it.
  - **One transaction = one aggregate** (commit a single aggregate atomically).
  - Reference **other aggregates by id**, never by object holding — keeps boundaries crisp and aggregates small.
- **Domain Event**: something meaningful that happened in the domain, past tense (`OrderShipped`), immutable, named in ubiquitous language. Drives side effects, integration, and cross-aggregate eventual consistency.
- **Repository**: collection-like abstraction to persist/retrieve **aggregate roots** (one repo per aggregate root). Domain code speaks `orders.findById()`, not SQL. Hides persistence.
- **Domain Service**: stateless domain logic that doesn't naturally belong to a single entity/VO (e.g. `TransferService` moving money between two `Account`s). Named in domain terms, holds no state.
- **Factory**: encapsulates complex creation of aggregates/VOs so they're born valid and invariants hold from birth.
- **Application Service**: thin orchestration layer (use-case), no business rules — loads aggregate, calls domain behavior, saves, publishes events, manages transaction. Distinct from domain service.

```text
API/UI → Application Service (use-case, tx) → Aggregate Root (invariants/behavior)
                                            → Repository (persistence)
                                            → Domain Service (cross-entity logic)
                                            ↳ emits Domain Events
```

## Aggregate design heuristics
- Design aggregates **small**; large aggregates = contention, big loads, lock conflicts.
- True invariants that must be immediately consistent → inside one aggregate. Everything else → eventual consistency across aggregates via domain events.
- Ask: "what MUST be consistent in the same transaction?" That set defines the boundary — not "what data is related."

## Event Storming
- Big-visual collaborative workshop with domain experts to explore a domain fast; sticky-note color code:
  - **orange** = domain event (past tense), **blue** = command, **yellow** = actor/user, **pink** = external system, **purple** = policy/reaction, **lilac** = hotspot/question, **green** = read model.
- Flow: flood domain events on a timeline → add commands + actors → group into aggregates → discover **bounded contexts** (seams where language changes).
- Cheap, high-bandwidth way to build ubiquitous language and find boundaries before writing code.

## CQRS / Event Sourcing link
- DDD pairs naturally with **CQRS** (separate write model = aggregates enforcing invariants; read model = denormalized query views).
- **Event sourcing**: persist the aggregate as its stream of domain events; current state = replay. Optional, powerful for audit/temporal domains, adds real cost. DDD does not require it.
- Aggregates as consistency boundaries map cleanly onto per-aggregate event streams.

## Sagas / process managers
- Cross-aggregate or cross-context workflows can't be one transaction → coordinate with a **process manager** (stateful) or **saga** (sequence of local transactions + **compensating actions** on failure).
- Reacts to domain events, sends the next command, tracks progress. Two flavors: **orchestration** (central coordinator) vs **choreography** (each service reacts to events, no coordinator).
- Use for "when X happens, eventually do Y and Z, and undo if a step fails" (order → reserve stock → charge → ship; compensate on any failure).

## Specification pattern
- Encapsulate a business rule/predicate as a first-class object (`OverdueInvoiceSpec.isSatisfiedBy(invoice)`); composable with `and`/`or`/`not`.
- Uses: validation, selection from a collection, building query criteria — keeps rules in the domain, named in ubiquitous language, and reusable.

## Module organization
- Package by **bounded context / feature**, not by technical layer (`billing/`, `catalog/` — not `controllers/`, `services/`, `repositories/` spanning all domains).
- Inside a context: keep domain model, application services, and infra adapters separated but colocated. Each context owns its schema/persistence.
- One deployable per context (microservices) or enforced modules in a modular monolith — either way, no direct reach across context internals.

## Layering / dependency direction
- Keep the **domain model pure** — no framework, ORM, HTTP, or DB types leaking in. Dependencies point inward toward the domain (see hexagonal/clean architecture).
- Persistence + I/O live in infrastructure; domain defines interfaces (repositories), infra implements them.
- **DTOs at the edge**: never expose aggregates directly over the wire; map to/from DTOs so the API contract and the domain model evolve independently.

## Pitfalls -> Fix
- **Anemic domain model** (entities are just getter/setter bags; logic in services) -> move behavior + invariants onto the aggregate; services orchestrate, not decide.
- **Huge "God" aggregates** (whole order + customer + catalog in one) -> split by true invariants; reference other aggregates by id; accept eventual consistency between them.
- **Leaking persistence into the domain** (ORM annotations, lazy-load proxies, `@Entity` driving the model) -> keep domain POJOs pure; map to persistence in infra; use repositories.
- **DDD everywhere** (tactical patterns on generic/CRUD subdomains) -> apply full DDD only to the **core** subdomain; buy generic, keep supporting simple.
- **Ignoring the ubiquitous language** (code names diverge from expert speech) -> rename to match domain terms; treat mismatches as modeling bugs.
- **Skipping strategic design** (jumping straight to entities/repos) -> establish subdomains, bounded contexts, and context map first; tactical patterns without boundaries just relabel a monolith.
- **Referencing other aggregates by object** (holding the whole `Customer` inside `Order`) -> hold `CustomerId`; load via repo when needed.
- **Spanning aggregates in one transaction** -> one aggregate per transaction; coordinate the rest with domain events + sagas/process managers.
- **Shared model across BCs** (one canonical `User` for all contexts) -> let each BC own its model; integrate via ACL / published language, not a shared schema.
- **Repository per entity** -> repository only per aggregate **root**; inner entities are loaded through the root.
- **Business logic in application services** -> application service only orchestrates (load/call/save/publish); rules belong in the domain.
- **Domain events used as an in-process god-bus for everything** -> reserve for genuine domain-meaningful facts; don't route trivial setter changes through events.
- **Modeling data instead of behavior** (ERD-first) -> start from commands/events/behavior; the data model follows the domain model.
