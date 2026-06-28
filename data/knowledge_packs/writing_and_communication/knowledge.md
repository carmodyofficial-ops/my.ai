# Technical Writing & Communication

## Know the Audience
- Name the reader: end user, maintainer, future-you? Match depth to it.
- State what they already know; skip it. Fill only the gap they need.
- Don't explain the obvious; don't assume the surprising.

## Lead With the Point (BLUF)
- First sentence = the answer/outcome. Then justify.
- Bad: "After investigation, we found..." Good: "Login fails on Safari; cause: cookie SameSite."
- PRs, emails, docs: conclusion up front, evidence below.

## Structure
- One idea per paragraph. Headers for scanning.
- Lists for parallel items, prose for flowing logic.
- Short sentences. Break any clause over ~25 words.

## Concision
- Active voice: "X parses Y" not "Y is parsed by X".
- Strong verbs over noun phrases: "decide" not "make a decision".
- Cut filler: "in order to"->"to", "due to the fact"->"because", "actually/basically/just".

## README
- What it is, why it exists, how to run, one runnable example. In that order.

## API Docs
- Per function: params (type+meaning), returns, raises, one example call.

## Commit Messages
- Imperative subject <=50 chars: "Add retry to upload". Blank line. Body = WHY, not what.
- Diff shows what changed; prose explains the reason and tradeoff.

## PR Descriptions
- What changed / why / how to test / risks. Keep each to a few lines.

## Code Comments
- Explain WHY, not what. `i++` needs no comment; a workaround does.
- Comment the surprising: hacks, non-obvious constraints, gotchas.

## Explaining
- Concrete example first, then the general rule. Analogy to bridge.
- Define jargon once, at first use; then reuse the term.

## Gotchas -> Fix
- Buried lede -> move conclusion to line 1.
- Wall of text -> headers + lists.
- Passive voice -> name the actor.
- Vague "this/it" -> name the noun.
- "should/might/maybe" -> state it or test it.
- Obvious comment -> delete it.
