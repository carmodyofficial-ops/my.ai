# Think Clearly, Learn Fast

## Reasoning
- **First principles**: derive from what's actually true here, don't paste a prior solution. Ask "what forces this?"
- **Decompose**: split into sub-problems that don't depend on each other; solve/parallelize separately.
- **Work backward**: state the goal concretely, ask "what must be true one step before?" Repeat to now.
- **Falsify**: hold 2-3 hypotheses. For each, name the observation that would *kill* it, then go look. Confirming evidence is cheap and lies.
- **Make assumptions explicit**: tag every claim `know / assume / must-check`. Bugs hide in unmarked assumes.
- **Edge/extreme cases**: 0, 1, empty, huge, negative, concurrent, null. Push variables to limits.
- **Fermi first**: estimate orders of magnitude before precise calc — catches 100x errors instantly. e.g. "10k rows x 1KB ~= 10MB, fits memory."

## Decisions under uncertainty
- List options; find the **one axis** that actually decides. Ignore the rest.
- **Reversible vs irreversible**: reversible -> just try it now. Irreversible -> slow down, gather evidence.
- Optimize **expected value**, not best case. Weight by probability.

## Counter these biases
- *Confirmation*: seek disproof. *Anchoring*: re-estimate from scratch. *Sunk cost*: judge on future value only. *Recency/availability*: check base rates, not the vivid last example.

## Learn fast
- **Map then drill**: sketch the 5 big pieces + how they connect before any detail.
- **By doing**: smallest experiment that returns signal. Run it.
- **Trace one real example** end-to-end through the actual system.
- **Teach it back**: explain aloud; the spot you stumble is your gap.
- **Spaced practice**: revisit at intervals, not in one cram.

## Gotchas
- Jumping to first plausible answer -> generate a 2nd.
- Confirming, not falsifying.
- Ignoring base rates.
- Analysis paralysis on reversible calls -> just ship.
- Memorizing trivia before the mental model.
