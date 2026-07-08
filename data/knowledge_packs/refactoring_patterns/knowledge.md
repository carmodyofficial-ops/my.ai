# Refactoring Patterns
## Core moves
- Extract function: name the *intent*, not the mechanics — `is_eligible_for_discount(order)` not `check_conditions(order)`. If you can't name it, you don't understand the block yet.
- Extract variable: replace a magic expression with a named intermediate; `const isOverdue = due < now && !paid` turns a comment into code.
- Inline is the inverse move: if a function/variable is a one-line pass-through with a worse name than its body, delete it. Indirection has a cost; only pay when it buys clarity.
- Rename discipline: rename in one dedicated commit with zero behavior change, using IDE/LSP rename (not find-replace — it misses shadowing, hits strings). Grep afterwards for the old name in docs, configs, serialized keys.
- Guard clauses over nesting: invert conditions, return early. Flatten `if (a) { if (b) { work } }` into `if (!a) return; if (!b) return; work`. Depth > 2 is a smell; the happy path should read top-to-bottom unindented.
- Replace conditional with polymorphism/map: a `switch`/`if-elif` chain on a type tag that appears in 2+ places -> dispatch table (`handlers: dict[str, Callable]`, `Record<Kind, Handler>`) or subclass method. One occurrence of the switch is fine; duplication is the trigger.
- Small steps with tests: every step compiles and passes tests; commit each mechanical step separately from behavior changes. Never mix "move code" and "change code" in one commit — the diff becomes unreviewable and the bug unfindable.

## Gotchas -> Fix
- **Refactor broke behavior "impossible" to break**: you refactored code with hidden effects (mutation, I/O, evaluation order). Fix: characterization tests first — pin current behavior (even buggy behavior) before touching legacy code.
- **Extracted function needs 7 parameters**: the block wasn't a coherent unit. Fix: extract a smaller piece, or introduce a parameter object / dataclass grouping the values that travel together.
- **Rename churned 400 files**: name was in serialized data, API payloads, or DB columns. Fix: rename only the code symbol; keep the wire/storage name via explicit mapping (`alias=` in pydantic, `@JsonProperty`, column name arg).
- **Boolean parameter added to share code** (`render(data, isCompact=True)`): flag argument smell — the function does two things. Fix: two functions, or strategy object; callers should read as intent.
- **Big-bang rewrite of legacy module stalls**: use strangler fig — route new calls through a facade, migrate one endpoint/use-case at a time behind it, delete old code when traffic hits zero. Both paths live simultaneously; a feature flag picks per-call.
- **Refactor PR mixes cleanup with a feature**: reviewers can't see the feature. Fix: refactor-first PR (no behavior change), feature PR second — "make the change easy, then make the easy change."
- **Test suite too slow/absent to refactor safely**: add a seam first — extract the target behind an interface, write fast tests against the seam, then refactor inside it.
- **Duplication removed too eagerly**: two code blocks that look alike but serve different domains will diverge; the shared helper sprouts flags. Fix: rule of three — tolerate duplication until the third occurrence proves the abstraction.

## Smells -> refactor
- Long function (screensful) -> extract function per intention-revealing step.
- Feature envy (method mostly reads another object's fields) -> move method to that object.
- Data clumps (same 3 args travel everywhere) -> parameter object.
- Shotgun surgery (one change touches many files) -> consolidate the concept into one module.
- Divergent change (one file changes for many reasons) -> split by responsibility.
- Primitive obsession (`str` user ids, `float` money) -> value types (`NewType('UserId', str)`, branded TS types); catches unit and identity mix-ups at type-check time.
- Comments explaining *what* -> extract + rename until the comment is redundant; keep comments that explain *why*.
- Dead code / commented-out code -> delete; git remembers.
- Speculative generality (unused hooks, single-implementation interfaces) -> inline and delete until a second implementation exists.

## When NOT to refactor
- Code you're about to delete or replace wholesale — don't polish the condemned.
- No tests and no time to add a seam: refactoring without a safety net is just editing.
- Mid-incident or right before release freeze — behavior-preserving is a claim, not a guarantee.
- Working code you merely find ugly but never touch: refactor along the paths you actively change ("boy scout rule" applies to campsites you visit).
- When the real problem is the design boundary, not the code: renaming variables inside a wrongly-placed module is lipstick; move the boundary instead.

## Mechanics that keep steps small
- Python: `functools.singledispatch` replaces isinstance chains; dataclasses replace tuple-passing; keyword-only args (`*,`) make call sites survive parameter reordering.
- TypeScript: discriminated unions + exhaustive `switch` with `never` check replace tag-checking `if` chains; `satisfies` keeps dispatch maps type-checked without widening.
- Parallel change (expand/contract) for public APIs: add the new signature, migrate callers, deprecate, remove — three deploys, zero breakage.
- Lean on the compiler: change a type, fix every red squiggle — the type-checker is your refactoring todo list. In Python, run `mypy`/`pyright` before and after; equal error counts is a cheap invariant.
- Keep a refactoring commit reviewable: `git diff --color-moved=dimmed-zebra` shows pure moves; reviewers verify "moved, not changed" in seconds.

## Sequencing a larger refactor
- Order: (1) characterization tests, (2) mechanical moves (rename, extract, move file) committed individually, (3) structural change (new interface/boundary), (4) behavior change, (5) delete dead paths. Reversing this order is how refactors get abandoned half-done.
- Extract-then-move beats move-then-edit: get the code into a named unit *in place*, prove tests pass, then relocate — two verifiable steps instead of one leap.
- Sprout method/class for adding features to untestable code: write the NEW logic in a fresh, tested function and call it from the legacy blob — the legacy code shrinks over time without a rewrite.
- Deprecation hygiene: mark the old symbol (`warnings.warn(..., DeprecationWarning)`, `@deprecated` JSDoc), point at the replacement in the message, set a removal date, and grep usage counts before deleting.
- Measure before performance-motivated refactors: profile first; "cleaner" and "faster" are different goals and often trade off. A refactor justified by speed needs a before/after benchmark in the PR.
- Extract-variable trick for debugging complex conditionals doubles as refactoring: each named sub-condition becomes inspectable and testable in isolation.
- Keep public API surface stable during internal refactors — re-export from the old path (`from new_module import Thing  # noqa`, barrel `export {Thing} from './new'`) so downstream imports survive; remove re-exports in a later major version.
