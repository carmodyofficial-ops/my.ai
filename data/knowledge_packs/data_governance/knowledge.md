# Data Governance

Policies + processes + tooling that make data **trustworthy, discoverable, compliant, and owned**. Goal: right people find the right data, trust it, and use it legally. Enable, don't gate.

## Why
- **Trust**: consumers know what a dataset means, how fresh, how correct, who owns it.
- **Discoverability**: find data without tribal knowledge; reduce duplicate/shadow datasets.
- **Compliance**: GDPR/CCPA/HIPAA/SOX — know where PII lives, control access, honor deletion/consent, audit.
- **Efficiency/quality**: fewer broken dashboards, less "which table is right?", faster onboarding.

## Data catalog + metadata
- Central searchable inventory of datasets/tables/columns/dashboards/models with **metadata**: description, owner, schema, tags, classification, freshness, popularity, lineage.
- Metadata types: **technical** (schema, types, partitions), **business** (glossary term, definition, KPI meaning), **operational** (freshness, row counts, last run, SLA), **social** (owner, usage, ratings, deprecation).
- **Business glossary**: canonical definitions ("active user", "revenue") mapped to physical columns → shared semantics.
- Tools: **DataHub, OpenMetadata, Amundsen** (open source); **Collibra, Alation, Atlan, Unity Catalog, Purview** (commercial/platform). Populate via automated ingestion + crawlers, not manual entry.

## Data lineage
- **Provenance**: end-to-end map of how data flows source → transform → table → dashboard (column-level ideally, not just table-level).
- **Impact analysis** (downstream): "if I change/drop this column, what breaks?" → find affected tables/dashboards/models before shipping.
- **Root-cause / upstream**: "this metric is wrong — which source/job caused it?"
- Captured automatically by parsing SQL/dbt/Spark/Airflow (dbt exposes lineage via manifest; OpenLineage/Marquez standardize events). Manual lineage rots.

## Data quality
- **Dimensions**: **accuracy** (matches reality), **completeness** (no missing required values/rows), **consistency** (agrees across systems, no contradictions), **timeliness/freshness** (up to date within SLA), **validity** (conforms to format/range/type), **uniqueness** (no dupes).
- **Checks**: not-null, unique/PK, referential integrity, range/domain (`0<=pct<=100`), regex/format, row-count deltas, freshness (max(ts) within N hours), distribution/anomaly (volume, null-rate, category drift), reconciliation vs source.
- **Monitoring**: run checks in-pipeline (block/alert on fail), scheduled, or observability platforms (**Monte Carlo, Soda, Anomalo, Great Expectations, dbt tests, Elementary**). Track SLAs/SLOs; alert owners; quality dashboards + scorecards.
- Fail modes: **circuit-break** (halt pipeline on critical failure) vs **warn** (log + alert) — classify checks by severity.

## Data contracts
- **Explicit agreement between producer and consumer** on a dataset's schema + semantics + guarantees (fields, types, nullability, semantics, freshness SLA, allowed changes, PII flags).
- **Enforcement**: validate at write/publish (schema registry, CI check on producer, gate in pipeline) so a breaking change fails **before** it reaches consumers — shift-left. Reject non-conforming data at the boundary.
- **Versioning**: **semantic-versioned** schemas; **backward-compatible** changes (add optional/nullable field) = minor; **breaking** (drop/rename/retype/tighten) = major → coordinate migration, dual-write/deprecation window. Avro/Protobuf schema registry (Confluent) enforces compatibility (`BACKWARD`/`FORWARD`/`FULL`).
- Kills the "silent upstream schema change broke everything" failure mode.

## Ownership & stewardship
- Every dataset has a named **owner** (accountable, decides schema/access) + **steward** (maintains quality, definitions, metadata). "No owner" = death of governance.
- **RACI** per domain; producers accountable for their data-as-a-product.

## Classification, PII & access/privacy
- **Classification tiers**: public / internal / confidential / restricted (or PII/PHI/PCI). Tag columns → drives access + masking + retention policy.
- **PII handling**: discover PII (scanners), tag, then **minimize** (collect only needed), **mask/tokenize/pseudonymize**, encrypt at rest/in transit, **retention limits** + deletion.
- **Access control**: RBAC/ABAC, least privilege, column/row-level security, dynamic masking by role. Audit access logs.
- **GDPR/CCPA link**: lawful basis + consent, **data subject rights** (access, rectification, **erasure/"right to be forgotten"**, portability), purpose limitation, data-minimization, DPIAs, breach notification, records of processing. Lineage + catalog are what make "find and delete all of this person's data" actually possible.

## Master Data Management (MDM)
- Single authoritative **golden record** for core shared entities (customer, product, supplier) across systems. Dedup/**entity resolution** (fuzzy match, survivorship rules), reconcile conflicting sources, canonical IDs. Prevents "3 customer tables that disagree".

## Data mesh
- Decentralized: **domain teams own their data as a product** (discoverable, addressable, trustworthy, self-describing, with SLAs) rather than a central team owning one monolithic lake/warehouse.
- Pillars: **domain ownership**, **data-as-a-product**, **self-serve data platform**, **federated computational governance** (global standards enforced automatically, local autonomy). Governance becomes a platform capability, not a committee.

## Tooling map
- Catalog/lineage: DataHub, OpenMetadata, Amundsen, Collibra, Atlan, Unity Catalog.
- Quality/tests: **dbt tests** (`unique`, `not_null`, `accepted_values`, `relationships`), **Great Expectations**, Soda, Monte Carlo, Elementary, Anomalo.
- Contracts/schema: Confluent Schema Registry (Avro/Protobuf), Buf, dbt contracts, data-diff.
- Access/privacy: Immuta, Privacera, cloud IAM + tag-based policies.

## Pitfalls -> Fix
- **Governance as bureaucracy** (approval boards, slow, everyone routes around it → shadow data). Fix: automate + embed in workflows (CI, catalog, contracts); federated/computational governance; make the governed path the easy path.
- **No ownership** ("everyone owns it = no one does"). Fix: assign a named owner + steward per dataset; block publishing without one.
- **Stale/empty catalog** (manual entry rots, nobody trusts or updates it). Fix: auto-ingest metadata from pipelines/warehouse; deprecation flags; usage-driven ranking; make it the search default.
- **No lineage** → can't do impact analysis or root-cause; every change is risky. Fix: automated column-level lineage from SQL/dbt/OpenLineage; wire into CI for impact checks.
- **Contract-less pipelines** → silent upstream schema/semantic changes break consumers. Fix: data contracts + schema registry with compatibility enforcement; producer CI gate; versioning.
- **Boiling the ocean** (govern everything at once → stalls, never ships). Fix: start with highest-value/most-used/most-sensitive datasets; iterate; prove value then expand.
- **Quality checks only at the end / dashboards** → bad data already consumed. Fix: shift-left, validate at ingestion/write; circuit-break critical failures; test in CI.
- **Alert fatigue** from noisy/low-severity checks. Fix: severity tiers, ownership-routed alerts, SLOs, dedup, mute known-benign.
- **PII sprawl / unknown PII** → compliance risk, can't fulfill deletion. Fix: automated PII discovery + tagging, classification-driven access + masking, retention + catalog/lineage to locate all copies.
- **Governance without executive buy-in / incentives**. Fix: tie to compliance risk + concrete cost of bad data; embed KPIs; leadership sponsorship.
- **Central bottleneck team** for a large org. Fix: data mesh — domain ownership + self-serve platform + federated standards.
- **Over-restrictive access** (nobody can get data → shadow copies). Fix: least-privilege but self-serve request + auto-grant by classification/role; balance access and control.
- **Duplicate/conflicting master entities**. Fix: MDM golden records, entity resolution, canonical IDs, survivorship rules.
```
