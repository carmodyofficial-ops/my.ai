# Threat Modeling

## What / why / when
- Structured process to find **what can go wrong** in a design before shipping, so you add mitigations early (cheap) not post-incident (expensive). Answers Shostack's 4 questions: **What are we building? What can go wrong? What are we going to do about it? Did we do a good job?**
- **When**: at design time for new features/services, on architecture change (new trust boundary, new data flow, new dependency), before major releases, and after incidents. **Shift-left**: earlier = cheaper. Re-model when the system changes — it's living, not a one-time doc.
- Output: prioritized **threats → mitigations**, tracked to closure (tickets), plus an updated model.

## Model the system: DFD + trust boundaries
- Build a **Data Flow Diagram (DFD)** with 4 element types: **external entities** (users, 3rd-party APIs), **processes** (services, functions), **data stores** (DBs, queues, caches, files), **data flows** (arrows, with protocol/direction).
- **Trust boundaries**: lines where privilege/trust changes — internet↔DMZ, browser↔server, service↔service, app↔DB, user-space↔kernel, tenant↔tenant. **Threats cluster where flows cross boundaries** — that's where to focus.
- Right altitude: one level deep enough to see boundaries and assets; decompose hot spots further. Include data classification (PII/secrets/PCI) on stores/flows. Note assumptions and who the **adversaries** are (external, malicious insider, compromised dependency).

## STRIDE — threat elicitation per element/flow
Walk each element and flow; ask each category. STRIDE = the violated property in parentheses.
- **S — Spoofing** (breaks *Authentication*): pretending to be another user/service/host. → strong authN, MFA, mTLS, signed tokens, no shared creds.
- **T — Tampering** (breaks *Integrity*): unauthorized modification of data in transit/at rest/in memory. → integrity checks (HMAC/signatures), TLS, input validation, access controls, immutable logs.
- **R — Repudiation** (breaks *Non-repudiation*): denying an action, no proof. → tamper-evident audit logs, timestamps, signed records.
- **I — Information disclosure** (breaks *Confidentiality*): leaking data. → encryption in transit/at rest, least privilege, minimize/mask data, error hygiene.
- **D — Denial of service** (breaks *Availability*): exhaust/crash. → rate limiting, quotas, autoscaling, timeouts, backpressure, circuit breakers.
- **E — Elevation of privilege** (breaks *Authorization*): gain rights you shouldn't. → server-side authZ on every action, deny-by-default, sandboxing, least privilege, patching.
- Per-element STRIDE bias: external entities → S,R; processes → all; data stores → T,I,R,D; data flows → T,I,D. (LINDDUN is the privacy-focused analogue.)

## Attack trees
- Root = attacker **goal** (e.g. "read another tenant's data"); branches = sub-goals; leaves = concrete steps. **AND** nodes (all children needed) vs **OR** nodes (any child). Annotate leaves with cost/skill/detectability to find cheapest paths → prioritize defenses on the weakest branch.
- Complements STRIDE: STRIDE is breadth (enumerate), attack trees are depth (reason about a specific goal).

## Abuse / misuse cases
- Invert user stories: "As an **attacker**, I want to …". Model the **evil path**, not just the happy path — automated abuse, business-logic abuse (coupon stacking, refund fraud, scraping), account takeover, rate abuse. Feeds requirements + tests.

## Risk rating & prioritization
- **DREAD** (Damage, Reproducibility, Exploitability, Affected users, Discoverability) — score each 1–3/1–10, average → rank. Simple but subjective; calibrate or you get noise.
- Alternatives: **CVSS** for known-vuln severity; **OWASP Risk Rating** (Likelihood × Impact); a plain 2×2 **Likelihood × Impact** matrix. Whatever the scale, prioritize by **risk = likelihood × business impact** and fix the top of the list first; accept/transfer/mitigate the rest explicitly.

## Mitigation mapping
- Each accepted threat → a **decision**: mitigate (control), eliminate (remove feature/data), transfer (insurance/3rd-party), or **accept** (documented, signed off). No silent drops.
- Map threats to **existing controls** and known patterns; reuse standards: OWASP ASVS/proactive controls, NIST 800-53, CIS benchmarks, cloud well-architected security pillars. Track each mitigation as a ticket with an owner + verification.

## Methodology comparison (pick to fit)
- **STRIDE** (Microsoft): threat-centric, per-element/interaction. Best default for engineering teams designing systems.
- **PASTA** (Process for Attack Simulation & Threat Analysis): 7-stage, risk/business-centric, attacker-simulation heavy — good for high-stakes, aligns security to business impact.
- **Attack trees**: goal-centric depth analysis.
- **LINDDUN**: privacy threats (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure, Unawareness, Non-compliance) — use alongside STRIDE for PII systems.
- **OCTAVE**: org-level risk assessment. **VAST**: scales across many teams via automation. Don't over-shop methods — consistency beats novelty.

## Worked mini-example (STRIDE on a login flow)
- Elements: browser (external), auth service (process), user/session store (data store), flow browser→auth crosses the internet trust boundary.
- **S**: attacker replays/steals a session token → mTLS/short tokens, rotate session ID on login.
- **T**: tamper JWT `role` claim → verify signature, pin alg, server-side authz.
- **R**: user denies a password change → signed, timestamped audit log.
- **I**: creds sniffed / user enumeration via error timing → TLS, uniform errors, constant-time compare.
- **D**: password-spray/lockout flood → rate limiting, exponential backoff, CAPTCHA.
- **E**: horizontal/vertical priv-esc via IDOR on account API → ownership checks, deny-by-default.

## In the SDLC
- **Shift-left**: threat model during design review; keep it lightweight and iterative. Lightweight methods that scale: **rapid/agile threat modeling**, **incremental** (model only the diff each sprint), Microsoft SDL, security cards, **"evil user stories"** in backlog.
- Automate where possible: **threat-model-as-code / pipeline** (e.g. YAML-defined DFDs generating threats), IaC scanning, and link findings to CI so drift is caught. Diagramming/threat tools: Microsoft Threat Modeling Tool, OWASP Threat Dragon, pytm (code-defined), IriusRisk. Don't let the tool replace the *thinking*.
- Feed results into requirements, secure design patterns, test cases (abuse cases → security tests), and pentest scope.

## Assets, adversaries, assumptions
- **Assets**: what's worth protecting — credentials/secrets, PII/PHI/PCI, money/transactions, intellectual property, availability of critical flows, integrity of audit logs. Rank threats by the asset at stake.
- **Adversaries** to enumerate explicitly: external attacker (opportunistic → targeted), **malicious insider**, compromised third-party/dependency/build pipeline, careless authorized user, automated bots. Each has different capability + motivation.
- **Assumptions & dependencies**: write them down — "TLS terminates at the LB", "the DB is only reachable from the app subnet", "the IdP validates MFA". A broken assumption is a latent threat; re-check them when infra changes.
- **Security requirements** fall out of the model: authN strength, authZ model, encryption, logging, rate limits, data retention/minimization — feed these into acceptance criteria.

## Quick-start recipe
1. Draw the DFD; mark trust boundaries + data classification.
2. List assets + adversaries + assumptions.
3. Walk each element/flow through STRIDE (attack tree for the crown-jewel goals).
4. Add abuse cases for business logic.
5. Rate + prioritize (likelihood × impact).
6. Assign a disposition + owner to each; file tickets; verify; keep the model in-repo.

## Pitfalls -> Fix
- **Boil-the-ocean** (model everything at once, never finish) -> scope to one feature/trust boundary per session; time-box; iterate.
- **No follow-through** (great doc, threats never fixed) -> convert every threat to a tracked ticket with owner + due date + verification; review at closure.
- **Stale model** (system changed, model didn't) -> re-model on architecture/data-flow changes; make it a design-review gate, keep it in-repo next to code.
- **Only the happy path** -> add abuse/misuse cases; explicitly ask "how would an attacker use this?".
- **Ignoring insiders & supply chain** -> include malicious insider + compromised dependency/vendor/build-pipeline as adversaries; model 3rd-party data flows and CI/CD.
- **Trust boundaries missing/wrong** -> the whole exercise hinges on these; explicitly draw every privilege change (tenant isolation, service-to-service, browser↔server).
- **Security team does it in isolation** -> engineers/architects/product in the room; they own the design and the fixes; security facilitates.
- **Analysis paralysis / over-detailed DFDs** -> right altitude; decompose only hot spots; prefer several small models over one giant one.
- **Subjective risk scores gamed to "low"** -> calibrate DREAD/likelihood-impact with examples; use business impact, peer-review ratings.
- **STRIDE checklist run mechanically** -> reason per element about realistic adversaries; pair with attack trees for high-value goals.
- **Threats without mitigations, or "accepted" without sign-off** -> every threat gets an explicit disposition (mitigate/eliminate/transfer/accept) recorded and owned.
- **Modeling too late** (after code freeze) -> do it at design; the cheapest fix is a design change.
