# Software Engineering Reference

## Structuring a change
- Smallest diff that fully solves it; don't reformat unrelated lines—it hides the real change in review.
- Match local conventions (naming, error style, imports) over your personal preference. Grep a sibling file first.
- One concern per commit/PR. Mixing a refactor with a behavior change makes both unreviewable.

## Error handling
- Fail loud on programmer errors and violated invariants (bad args, impossible states): raise/throw, don't return null.
- Degrade only on expected external failures (network, missing file) and only where you can act—retry, fallback, or surface a clear message.
- Catch at the boundary where you have context to handle it, not at the throw site. Never `catch {}` swallow; at minimum log with cause.
- Validate inputs at the API boundary, then trust them inward. Don't re-check the same thing in every layer.

## API & function design
- Make contracts explicit: narrow types over `any`/`dict`, enums over magic strings, non-null over optional-everywhere.
- Return one type per function. Don't return `T | false | null`; pick a sentinel and document it.
- No boolean trap params (`f(true, false)`)—use keyword args or an options object.
- Pure core, side effects at the edges. Easier to test and reuse.

## Refactoring safely
- Tests green BEFORE you touch it. No tests? Add a characterization test capturing current behavior first.
- Behavior-preserving steps, run tests between each. Don't refactor and add features in one move.

## Abstraction
- Inline until the third duplication (rule of three). Two similar blocks that drift differently aren't duplication.
- A wrong abstraction costs more than copy-paste—prefer a little duplication over a leaky base class.

## Naming
- Name for what it means, not how it's built (`activeUsers`, not `filteredList`). Booleans read as predicates (`isReady`).

## Review red flags
- Functions >~40 lines, >3 nesting levels, params unused, TODO with no ticket, commented-out code, swallowed errors, off-by-one at loop bounds.

## Tech debt
- Take it knowingly with a ticket/comment naming the tradeoff; refuse it silently in core paths that are costly to change later.
