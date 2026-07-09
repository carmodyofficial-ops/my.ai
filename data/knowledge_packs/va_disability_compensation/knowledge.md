# VA Disability Compensation — Working Reference

Authoritative sources: **38 CFR Part 3** (service connection) and **Part 4** (the
Schedule for Rating Disabilities / "VASRD") on eCFR, and **VA.gov**. Public-domain US
federal material. The schedule is amended over time (e.g., 2024–2025 musculoskeletal,
mental, and respiratory updates) — **cite the section/diagnostic code and verify against
current eCFR/VA.gov before relying on any criterion or amount.** This is reference
information, **not** a claim determination.

## Keep two questions separate
1. **Service connection** (Part 3) — is the disability linked to service? Needs (1) a
   current diagnosis, (2) an in-service event/injury/exposure, and (3) a medical
   **nexus** linking them. This pack assumes connection is established.
2. **Rating** (Part 4) — how disabling is it? Each condition gets a **diagnostic code
   (DC)** and a percentage from its criteria. Ratings reflect **average impairment of
   earning capacity** (§4.1), not symptoms in isolation.

## Core rules
- Assign the level the documented picture **more nearly approximates** (§4.7);
  reasonable doubt goes to the claimant (§4.3).
- **No pyramiding** (§4.14): the same symptoms can't be rated under two codes.
- **Analogous rating** (§4.20): an unlisted condition is rated under the closest listed DC.
- **0% (noncompensable)** still establishes service connection — valuable if the
  condition later worsens.

## Combining ratings — NOT addition (§4.25)
Multiple disabilities combine on **remaining efficiency**: each rating applies to what's
left after the prior one. Example: 50% then 30% → 50% + (30% of remaining 50%) = 65% →
**rounded to nearest 10% = 70%** (not 80%). Use the Combined Ratings Table (§4.25).
- **Bilateral factor** (§4.26): paired extremities (both arms / both legs) get an extra
  10% of their combined value, applied **before** combining with the rest.

## TDIU — total disability based on individual unemployability (§4.16)
Pays at the **100% rate** without a 100% schedular rating when service-connected
disabilities prevent **substantially gainful employment**. Typical schedular threshold:
one disability ≥60%, **or** a combined ≥70% with at least one ≥40% (otherwise an
extra-schedular referral under §4.16(b)/§3.321).

## High-frequency rating criteria (condensed — confirm in `sections/` + eCFR)

**Mental disorders — §4.130, General Rating Formula** (PTSD DC 9411, MDD 9434, GAD 9400,
etc., all on one formula; rate the *overall* occupational/social impairment, not a symptom
count):
- **100%** total occupational and social impairment.
- **70%** deficiencies in most areas (work, school, family, judgment, thinking, mood).
- **50%** reduced reliability and productivity.
- **30%** occasional decrease in work efficiency / intermittent task inability.
- **10%** mild or transient symptoms / controlled by continuous medication.
- **0%** diagnosed but not severe enough to impair function or need medication.

**Tinnitus — §4.87, DC 6260:** a single **10% maximum**, whether one ear or both.

**Sleep apnea — §4.97, DC 6847** (verify; this DC was under amendment): **0%**
asymptomatic with documented sleep-disordered breathing; **30%** persistent daytime
hypersomnolence; **50%** requires a breathing-assistance device (e.g., CPAP); **100%**
chronic respiratory failure with CO₂ retention, cor pulmonale, or requires tracheostomy.

**Migraines — §4.124a, DC 8100** (by *characteristic prostrating* attacks): **0%** less
frequent; **10%** averaging one in 2 months over the last several months; **30%**
averaging once a month; **50%** very frequent, completely prostrating and prolonged
attacks productive of **severe economic inadaptability**.

**Spine — §4.71a, General Rating Formula** (thoracolumbar, by forward flexion / combined
ROM / ankylosis; cite exact degrees from §4.71a): roughly **10%** flexion >60°≤85°;
**20%** >30°≤60° (or muscle spasm causing abnormal gait/contour); **40%** flexion ≤30°
or favorable ankylosis of the whole thoracolumbar spine; **50%** unfavorable ankylosis of
the whole thoracolumbar spine; **100%** unfavorable ankylosis of the entire spine.
Painful motion adds a minimum compensable rating (§4.59); consider §4.40/§4.45 functional
loss.

## Where the rest lives
- **Full schedule:** `sections/sec_4_x.md` — ~92 cited §4.x files (every rating
  schedule), indexed in `vasrd_index.json`. Read the exact DC there before quoting.
- **Monthly payment rates:** `comp_rates.md` (effective each December 1 with the COLA —
  re-verify against VA.gov).
- **Framework/criteria detail:** `overview.md`, `reference.md`.

## Boundaries
Reference only — never tell a user they "qualify for X%" (that's a VA adjudication on the
evidence of record). Never invent a percentage, code, criterion, or dollar amount; if a
value isn't sourced, say so. For a real claim, refer to an accredited VSO/attorney and
VA.gov.
