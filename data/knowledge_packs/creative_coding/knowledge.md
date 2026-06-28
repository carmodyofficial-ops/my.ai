# Creative Problem-Solving Techniques for Coding

Apply these to invent a solution FITTED to the problem, not recite the most common template.

## First Principles
Strip "how it's usually done." Ask: *what does the data/spec truly require, and what's the minimum that satisfies it?* A "rate limiter" may just need `last_ts + n` arithmetic, not a token-bucket class.

## Diverge, Then Converge
Sketch 2-3 *structurally different* solutions before coding: table-driven vs `if/elif`; recursion vs explicit stack; precompute lookup vs compute-on-demand; declarative schema vs imperative steps. Pick or fuse the best — don't grab the first.

## Invert
Solve the opposite or work backward from the output. Instead of "filter valid items," remove invalid ones. Build the desired final string, then derive the parser. Compute reachable-from-end, not from-start.

## Relax & Tighten Constraints
"If memory were free?" → precompute a full lookup table. "If I had only 10 lines?" → forces a unifying abstraction. "Infinite time?" → brute force may be correct-enough. Extremes expose the real design.

## Simplify Radically
"What makes this 10x simpler?" Delete the requirement, merge near-identical branches, replace inheritance with a dict of functions. Often a config map kills 80 lines of conditionals.

## Transfer / Analogy
Borrow a shape from another domain: a state machine for UI flow, a pipeline for transforms, an event bus for decoupling, a cache for repeated work, a query planner for ordering operations.

## Combine Patterns
Fuse two known patterns for THIS case: memoized recursion = DP; visitor + pipeline; registry + factory via a decorator that self-registers handlers.

## Data-First
Design the data shape first; code falls out. Replace `switch(type)` with `RULES = {type: handler}`. Model state as one struct, not 5 scattered flags. Right structure → trivial logic.

## Question the Spec
Is the literal ask the real need? "Add a retry button" may really mean "make it not fail." Offer the better thing.

## Anti-Boilerplate
Never paste the canonical template. Tailor names, structure, and edge handling to this context. Generic code is a smell — if it'd fit any project, it fits none well.
