# Design Patterns & Architecture

Pick the pattern that FITS the problem, not the fanciest.

## SOLID
- **S**RP: one reason to change per module.
- **O**CP: extend without editing existing code.
- **L**SP: subtypes must honor the base contract.
- **I**SP: small focused interfaces, not fat ones.
- **D**IP: depend on abstractions, inject deps.

## GoF — useful ones
- **Strategy**: swap algorithms at runtime. `sort(data, key=cmp)`.
- **Factory**: decouple creation from use. `make_parser(fmt)`.
- **Observer**: pub/sub events. `bus.on("save", handler)`.
- **Decorator**: wrap to add behavior. `@retry @cache def f()`.
- **Adapter**: bridge incompatible APIs. `StripeAdapter(PaymentPort)`.
- **Command**: action as object -> queue/undo. `cmd.execute()`.
- **Builder**: stepwise complex objects. `Query().where().build()`.
- **Singleton**: rare; prefer DI. Hidden global = test pain.

## Core principles
- Composition over inheritance: has-a beats is-a; inherit only true subtypes.
- Dependency injection: pass collaborators in; don't `new` them inside.
- Separation of concerns: keep IO, logic, and state apart.
- Rule of three: don't abstract until the 3rd duplication. Wrong abstraction costs more than duplication.

## Architecture styles
- **Layered**: UI->service->data. Simple, can get anemic.
- **Hexagonal (ports/adapters)**: core logic + pluggable IO at edges. Testable.
- **Event-driven**: async, decoupled; harder to trace.
- **CQRS**: split read/write models. Only for real read/write skew.
- **Monolith vs microservices**: start monolith; split for scaling/teams, not fashion. Distribution adds network, ops, consistency cost.

## Gotchas
- Over-engineering: indirection that adds no value.
- Premature abstraction: YAGNI — solve today's problem.
- God objects: split classes that know/do everything.
- Deep inheritance: >2-3 levels is fragile; flatten.
- Leaky abstractions: exposing internals defeats the wrapper.
- Singletons as global state: hidden coupling, untestable.
