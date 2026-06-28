---
name: creative-engineering
description: "How to design an ORIGINAL, fitted solution instead of regurgitating the most common template: diverge to several genuinely different approaches, reason from first principles and the data, then converge on the one that fits this exact problem."
version: 1.0.0
category: Coding
tags: [creative, creativity, design, original, novel, unique, approach, architecture, brainstorm, invent, elegant, refactor, hard problem, ambiguous, greenfield, idea]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use for non-trivial design — a new feature/system, a hard or open-ended problem, a greenfield build, or anytime the "obvious" solution feels like boilerplate. The goal is a solution invented for THIS problem, not the generic one you've seen most.

## Procedure

1. State the real problem from first principles: what does it actually require, given the real inputs/constraints/data? Strip away how it's "usually done" — that's a prior, not a requirement. Note the one or two constraints that dominate.
2. DIVERGE — generate 2-3 genuinely different approaches, not three flavors of the same one. Vary a real axis: the data model (table/config-driven vs branching logic), the paradigm (declarative vs imperative, event-driven vs polling), the timing (precompute vs compute-on-demand), or borrow a pattern from another domain (state machine, pipeline, cache, query planner, game loop) if it fits. For each, one line on its key idea + main tradeoff.
3. Pressure-test with extremes: "what if memory/time were free?" and "what if I had only 10 lines?" The extremes expose a simpler or sharper design than the middle-of-the-road one. Ask "what would make this 10x simpler?" — usually a better data shape or a unifying abstraction that collapses the special cases.
4. CONVERGE — pick the approach that best fits the real constraints, or synthesize the best parts of two. Prefer the design that makes the rest of the code trivial. Justify the choice in one sentence (why it beats the others HERE).
5. Question the spec once: is the literal request the real need? If a slightly different thing is clearly better, say so and offer it.
6. Implement it tailored to this context — names, structure, and edge handling fitted to the real problem, not copy-pasted from the canonical version.

## Pitfalls

- Reaching for the most common pattern reflexively — it's the most probable, which is exactly why it's generic. Probable != best.
- "Diverging" into three near-identical options. If they share the same data model and control flow, you haven't diverged.
- Cleverness for its own sake. Original means BETTER-FITTED and simpler, not obscure. The bar is "this makes the problem easy," not "this is unusual."
- Over-abstracting a one-off. Tailored can mean small and direct.
- Pasting the textbook implementation and changing only the names.

## Verification

- You can name 2-3 genuinely different approaches you considered and why you chose this one.
- The design is driven by THIS problem's constraints/data, not a default template.
- It's the simplest design that makes the problem easy, with edge cases handled for the real inputs.
