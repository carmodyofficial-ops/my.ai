# Memory Hooks — VA Disability Compensation

When to recall this pack:
- The user mentions VA disability, service connection, a rating percentage, a diagnostic
  code, a C&P exam, TDIU, combined ratings, or a specific condition + "VA rating".
- Questions about how much VA compensation pays per month (→ `comp_rates.md`).

What to anchor on:
- Rating criteria + percentages live in `sections/sec_4_x.md` (full 38 CFR Part 4),
  indexed in `vasrd_index.json`; the framework is in `overview.md`; dollar amounts in
  `comp_rates.md` (effective date matters — they change yearly).
- Always **cite the section/diagnostic code** and the VA.gov rate effective date.
- Keep **service connection** (linkage) separate from **rating** (severity).

What NOT to do (see `safety_boundaries.md`):
- Don't invent percentages, codes, criteria, or dollar amounts. If unsure, say so and
  point to eCFR / VA.gov.
- Don't tell a user they "qualify for X%" — that's a VA determination, not a checklist.
- Don't treat this as legal/medical/claims advice.

Freshness: re-run `scripts/ingest_va_vasrd.py` after VASRD amendments; re-check
`comp_rates.md` against VA.gov after each annual COLA (rates effective every December 1).
