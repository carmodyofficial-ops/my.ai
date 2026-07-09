# RAG Memory Retrieval Discipline Guard

Updated: 2026-06-22T01:00:24.487450+00:00

## Separation of concerns

Do not conflate:

- Knowledge packs.
- User memory.
- Benchmark cases.
- Benchmark answers.
- Runtime prompt context.
- Tool outputs.
- Source files.
- Git-tracked reports.

## Benchmark leakage rule

Benchmark answers must not be added to knowledge packs. Doing so contaminates future evaluations.

Benchmark cases may live under eval directories. They are for testing, not retrieval-grounded answering.

## Memory write discipline

Memory is appropriate when the user explicitly asks to remember something or when stable long-term project context would improve future responses.

Memory is not appropriate for:

- Random terminal noise.
- Short-lived shell state.
- Secrets.
- Credentials.
- Sensitive personal data unless explicitly requested.
- Benchmark answers.

## Retrieval calibration

When retrieval selects broad packs but misses precise packs:

1. Classify as REVIEW, not failure by default.
2. Check runtime function signatures.
3. Check selector implementation path.
4. Verify selected pack IDs.
5. Distinguish broad-pack partial success from precision-pack failure.
6. Run a corrected calibration before patching.
7. Avoid overclaiming.

## Knowledge-pack hygiene

Knowledge packs should have:

- `knowledge.md`
- `metadata.json`
- where needed, `manifest.json`
- where needed, `source_index.json`
- no secrets
- no benchmark answer leakage
- clear purpose and boundaries
