# State Machines & Statecharts

## Why FSMs (the core payoff)
- Model behavior as **explicit finite states + allowed transitions** instead of a soup of boolean flags. Makes **impossible states impossible** and unhandled cases visible.
- Replaces `isLoading && !isError && data` combinatorics: 4 booleans = 16 combos, most nonsensical; a machine has exactly the valid states you declared.
- Benefits: self-documenting, visualizable, testable (states + transitions are enumerable), predictable (an event in a state either has a defined transition or is ignored — no surprise paths).

## FSM anatomy
- **State**: a named mode the system is in; exactly one active (in a flat FSM). `idle`, `loading`, `success`, `error`.
- **Event** (trigger): input that may cause a transition. `FETCH`, `RESOLVE`, `RETRY`.
- **Transition**: `state --event[guard]/action--> state`. Fired by an event in a source state.
- **Guard** (condition): boolean predicate gating a transition; **pure, side-effect-free**. If false, transition doesn't fire.
- **Action** (effect): side effect run on transition, or on state **entry/exit**. Where side effects belong — not in guards.
- **Final state**: terminal; no outgoing transitions.
- Two classic formalisms: **Mealy** (output depends on state + input → actions on transitions) and **Moore** (output depends on state only → actions on entry). Most practical machines mix both.

```text
idle --FETCH--> loading
loading --RESOLVE--> success
loading --REJECT[canRetry]--> retrying
loading --REJECT[!canRetry]--> error
retrying --FETCH--> loading
```

## Statecharts (Harel) — FSMs that scale
- Solve **state explosion** by adding structure to plain FSMs:
- **Hierarchical / nested (compound) states**: a state contains sub-states. An event handled by no child bubbles to the parent → shared transitions declared once (e.g. a global `CANCEL` on the parent applies to all children).
- **Parallel / orthogonal regions**: multiple independent sub-machines active **simultaneously** within one state (e.g. a text editor's `bold` × `italic` × `saved/dirty`). Avoids multiplying states = cross product.
- **History states**: re-entering a compound state resumes its **last active** sub-state — **shallow** (top level) or **deep** (full nested path).
- **Entry/exit actions**: run whenever a state is entered/left, regardless of which transition — robust place for setup/teardown.
- **Guarded / eventless (always) transitions**: automatically taken when a condition holds (transient states).

## XState (the JS/TS implementation)
- `createMachine({...})` defines states/events/transitions declaratively; an **actor** (`createActor(machine).start()`) is a running instance you `.send(event)` to.
- **context** = the machine's extended state (quantitative data: retry count, form values) alongside the finite state. Updated via `assign(...)` actions.
- **actions**: `entry`, `exit`, transition actions; side effects. **guards** gate transitions. **Delays/`after`** for timeouts.
- **invoke / actors**: spawn async work (promises, callbacks, observables, or child machines) tied to a state's lifecycle — auto-cancelled on state exit. Model "loading" as `invoke: { src: fetchUser, onDone, onError }`.
- **Actor model**: machines communicate by **sending events**, can spawn child actors, and isolate state — no shared mutable state; message-passing concurrency.
- Statechart JSON is serializable → visualizable + inspectable (Stately viz / inspector).

```js
const machine = createMachine({
  id: 'fetch', initial: 'idle',
  context: { data: null, retries: 0 },
  states: {
    idle:    { on: { FETCH: 'loading' } },
    loading: { invoke: { src: 'fetchData', onDone:  { target: 'success', actions: assign({ data: ({event}) => event.output }) },
                                            onError: { target: 'failure' } } },
    success: { type: 'final' },
    failure: { on: { RETRY: { target: 'loading', guard: 'canRetry' } } },
  },
});
```

## UI state modeling
- Canonical async triple: `idle → loading → (success | error)`, with `error → loading` on retry. Kills the boolean-flag mess and the "flash of both spinner and error" bugs.
- Model form/wizard/checkout flows, media players, connection lifecycles, auth flows, and drag-drop as machines — anything with modes + rules.

## Execution semantics (statecharts)
- Processing an event runs a **microstep** (a set of simultaneous transitions); the machine settles through microsteps to a stable configuration = one **macrostep**. Eventless/"always" transitions drive microsteps until none apply.
- **Run-to-completion (RTC)**: an event is fully processed (all resulting actions + transitions) before the next event is handled — no interleaving. Events arriving mid-processing queue.
- Transition action order on a state change: **exit actions** (innermost→out) → **transition actions** → **entry actions** (outer→in). Deterministic and worth knowing when effects seem to fire "in the wrong order."
- Formal lineage: FSM → **pushdown automaton** (adds a stack, e.g. nested modals/undo) → Turing machine. **SCXML** is the W3C XML standard for statecharts; XState implements SCXML-compatible semantics.

## vs reducers / Redux
- A Redux reducer is `(state, action) => state` with **no constraint** on which actions are valid in which state — same boolean-explosion trap in a different shape.
- A state machine adds the missing piece: transitions are **only** defined per state, so invalid (state, event) pairs are structurally impossible. You can drive a reducer *with* a machine, or use XState instead.
- Machines make the **finite** (qualitative modes) explicit and keep the **infinite** (quantitative data) in context — reducers blur the two.

## Testing & visualization
- Test transitions exhaustively: for each (state, event) assert the resulting state, context, and actions. Enumerable → high coverage cheaply.
- **Model-based testing**: derive test paths from the machine graph to cover every transition automatically (`@xstate/test`-style).
- Assert **guards** in isolation (pure functions) and that invalid events are **ignored** (no transition), not crashing.
- Visualize the chart to review with non-engineers — the diagram *is* the spec.

## Actors & communicating machines
- **Actor model**: each actor owns private state, processes messages one at a time, and communicates only by sending messages — no shared memory. A running machine *is* an actor.
- Compose systems as a tree of actors: a parent **invokes/spawns** children, children **send events up** (or the parent references them). Model a page as a parent machine coordinating child machines (form, modal, fetch) rather than one monolith.
- Maps cleanly to real concurrency (Erlang/Elixir processes, Akka) and to UI: isolate, message-pass, supervise. Enables independent testing + reasoning per actor.

## When FSM vs simple state
- Use a machine when: >2 booleans interact, "impossible" combinations keep appearing, transitions have rules/order, or bugs are "it got into a weird state."
- Skip it for genuinely independent toggles or a single boolean — a machine there is overhead.
- Escalate flat FSM → statechart when states multiply; reach for parallel regions before duplicating states.

## Pitfalls -> Fix
- **Boolean explosion** (`isLoading`, `isError`, `isSuccess`, `isEmpty` all coexisting) -> collapse into one enumerated state; derive booleans from it.
- **Impossible/contradictory states** (loading true AND error set) -> make illegal states unrepresentable via a single finite state; use a discriminated union / machine.
- **Implicit transitions** (state changed by scattered `setState` calls with no rule) -> centralize all changes in explicit transitions; state only changes via `send(event)`.
- **Side effects in guards** (guard mutates, calls API, logs) -> keep guards pure predicates; put effects in entry/exit/transition actions.
- **Unhandled events cause crashes/undefined behavior** -> define behavior for every event per state (transition, self-transition, or explicit ignore); rely on the machine to no-op undefined ones.
- **God machine** (one giant flat chart with dozens of states) -> decompose with hierarchy + parallel regions or spawn child actors; nest shared handling on parents.
- **Storing derived data as state nodes** (a state per data value) -> keep quantitative/extended data in `context`; reserve finite states for qualitative modes.
- **Effects not tied to lifecycle** (fetch keeps running after leaving `loading`) -> use `invoke` so async work is cancelled on state exit; teardown in `exit` actions.
- **Reinventing async by hand** (manual promise + flags inside a machine) -> model it as an invoked actor with `onDone`/`onError`.
- **Over-modeling** (statechart for a single checkbox) -> reserve FSMs for genuine multi-mode/rule-bound behavior.
- **Guard order ambiguity** (multiple transitions on same event, unclear winner) -> order matters (first matching guard wins); make guards mutually exclusive or explicitly ordered.
- **Losing sub-state on re-entry** (wizard restarts from step 1) -> use history states (shallow/deep) to resume.
