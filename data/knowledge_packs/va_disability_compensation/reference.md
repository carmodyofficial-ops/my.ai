# VA Rating Criteria Reference (38 CFR Part 4)

Per-condition rating criteria. **Every entry cites its eCFR section.** Percentages
and criteria are from 38 CFR Part 4 (current eCFR). This is reference text — verify
against the live regulation before relying on it (the schedule is amended over time).
Ratings apply only *after* service connection is established.

Format: **Body system → diagnostic code(s) / condition → level: criteria.**

---

## Mental disorders — §4.130 (General Rating Formula for Mental Disorders)

Applies to most service-connected mental conditions (e.g., PTSD DC 9411, major
depressive disorder DC 9434, generalized anxiety DC 9400, etc.). All are rated on the
**same general formula** by overall occupational and social impairment:

- **100%** — Total occupational and social impairment, due to such symptoms as:
  gross impairment in thought processes or communication; persistent delusions or
  hallucinations; grossly inappropriate behavior; persistent danger of hurting self
  or others; intermittent inability to perform activities of daily living (including
  personal hygiene); disorientation to time or place; memory loss for names of close
  relatives, own occupation, or own name.
- **70%** — Occupational and social impairment with **deficiencies in most areas**
  (work, school, family relations, judgment, thinking, mood), due to such symptoms
  as: suicidal ideation; obsessional rituals interfering with routine activities;
  intermittently illogical/obscure/irrelevant speech; near-continuous panic or
  depression affecting ability to function independently; impaired impulse control;
  spatial disorientation; neglect of personal appearance/hygiene; difficulty
  adapting to stressful circumstances; inability to establish/maintain effective
  relationships.
- **50%** — Occupational and social impairment with **reduced reliability and
  productivity**, due to such symptoms as: flattened affect; circumstantial/
  circumlocutory/stereotyped speech; panic attacks more than once a week; difficulty
  understanding complex commands; impairment of short- and long-term memory;
  impaired judgment; impaired abstract thinking; disturbances of motivation and mood;
  difficulty establishing/maintaining effective work and social relationships.
- **30%** — Occupational and social impairment with **occasional decrease in work
  efficiency** and intermittent inability to perform tasks, due to such symptoms as:
  depressed mood, anxiety, suspiciousness, panic attacks (weekly or less), chronic
  sleep impairment, mild memory loss.
- **10%** — Occupational and social impairment due to **mild or transient symptoms**
  that decrease work efficiency only during significant stress, or symptoms
  controlled by continuous medication.
- **0%** — A mental condition formally diagnosed, but symptoms not severe enough to
  interfere with occupational/social functioning or require continuous medication.

Notes: rate the *overall* picture, not a symptom count (symptoms are "such symptoms
as" examples). Eating disorders (§4.130 DC 9520-9521) use a different, weight/
hospitalization-based formula. Source: eCFR Title 38 §4.130.

---

## Full schedule — all body systems

The complete 38 CFR Part 4 schedule is ingested into `sections/` (one cited file per
§4.x section, ~92 sections incl. all ~35 rating schedules), pulled verbatim-faithful
from eCFR (issue date in `manifest.vasrd_issue_date`) with diagnostic codes,
condition names, symptom/severity criteria, and percentages. Index: `vasrd_index.json`.
Re-run `scripts/ingest_va_vasrd.py` to refresh when the regulation is amended.

Common references: musculoskeletal/spine & joints §4.71a · muscle injuries §4.73 ·
eye §4.79 · hearing §4.85-4.87 (tinnitus DC 6260 = 10%) · respiratory incl. sleep
apnea §4.97 (DC 6847) · cardiovascular §4.104 · digestive §4.114 · skin/scars §4.118 ·
neurological incl. migraines §4.124a (DC 8100) · mental §4.130. Always cite the
section/diagnostic code and confirm against current eCFR.
