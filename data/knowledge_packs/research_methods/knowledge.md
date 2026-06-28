# Investigation & Research Methods

## 1. Define the question
State precisely what you're answering and why. Ask: *what decision does this change?* If no answer alters action, stop. Scope it: version, platform, timeframe, constraints. Bad: "is X fast?" Good: "is X's p99 < 50ms for 10k writes/s on v2.3?"

## 2. Source strategy
Primary > secondary. Source code, official docs, specs, RFCs, changelogs > blogs > forums > AI summaries. For fast-moving tech, recent > stale (check dates; a 2019 answer may be wrong). Require >=2 independent sources before trusting a non-trivial claim.

## 3. Evaluate sources
Weigh authority (who wrote it, do they own the system?), recency, bias (vendor selling something), corroboration. Separate **fact** (verifiable), **opinion** (judgment), **speculation** (guess). Label which you're relaying.

## 4. Search technique
Use specific terms, not vague ones. Paste error strings verbatim in quotes. Use `site:` (e.g. `site:docs.python.org`), version numbers, and GitHub code/issue search. Then *open and read* the doc or source — don't trust the snippet or an SEO listicle.

## 5. Debugging-as-research
Reproduce first — never theorize before you've seen it fail. Isolate one variable at a time. Form an explicit hypothesis ("if it's the cache, clearing it fixes it"), then test it. Don't guess-and-patch; let the evidence pick the cause.

## 6. Synthesis
Collect evidence, state the consensus AND the disagreements explicitly. Attach confidence (high/med/low) and why. Cite each claim with a link/path so it's checkable. "Per <source>, X; but <source2> contradicts on Y."

## 7. Know when to stop
Stop when you have enough to decide or act, and added searching only repeats known points. Avoid analysis paralysis; ship the answer with its confidence and open questions.

## Gotchas
- Confirmation bias: actively seek disconfirming evidence.
- Single-source claims: corroborate or flag.
- Stale / SEO-spam content: check date and author.
- Accepting a summary without reading the primary.
- Theorizing before reproducing.
- Uncited assertions — if you can't cite it, say so.
