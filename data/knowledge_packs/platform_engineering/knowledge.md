# Platform Engineering

## Core idea
- Build an **Internal Developer Platform (IDP)**: a curated, self-service layer of tools/services/workflows that lets product teams ship independently without deep infra expertise.
- Goal = **reduce developer cognitive load** and remove friction, so devs focus on business value not YAML/IAM/pipelines. Measured by developer productivity + experience, not infra output.
- **Platform-as-a-Product**: run the platform like a product — internal developers are **customers**, adoption is voluntary and earned, you do discovery, roadmaps, versioning, support, and measure satisfaction. Not a ticket queue.

## Golden paths / paved roads
- **Golden path (paved road)**: an opinionated, supported, well-documented default route to build/ship a common type of service — the "easy button" that bakes in best practices (CI/CD, observability, security, scaffolding) so the right way is the easy way.
- Covers 80% of use cases; teams can leave the path but then own the extra work (guardrails, not gates).
- Ideally self-service end to end: `scaffold new service → repo + pipeline + infra + dashboards + on-call` in minutes.

## Self-service
- Provision environments, databases, queues, DNS, secrets, and deployments **without a ticket** — via portal, CLI, API, or PR to config.
- Backed by IaC (Terraform/Crossplane/Pulumi) + templates; the platform abstracts them behind a simpler interface. Think "self-service with sane defaults," not "here's raw Terraform."
- Ephemeral/preview environments per PR are a hallmark capability.

## Guardrails vs gates (paved road vs mandate)
- **Guardrails**: safe defaults + policy-as-code (OPA/Kyverno, org policies) that make insecure/expensive choices hard by default but don't block. **Enable**, don't mandate.
- **Gates**: hard blockers/approvals. Minimize; each gate you add moves the platform toward gatekeeper.
- Adoption is won by making the paved road genuinely better (faster, safer, less toil) — not by forcing it.

## Team Topologies framing
- **Platform team**: builds + runs the IDP as a product; reduces cognitive load for stream-aligned teams.
- **Stream-aligned team**: product/feature teams — the platform's customers.
- **Enabling team**: coaches/upskills stream teams (temporary, capability transfer). Distinct from platform (which provides a *service*, ongoing).
- **Complicated-subsystem team**: owns a specialized hard component.
- **Thinnest Viable Platform (TVP)**: start with the smallest thing that reduces load — could be a wiki page of paved-road docs, not a full portal. Grow only as real demand proves value. Avoid building a big platform speculatively.

## Backstage (developer portal)
- CNCF developer portal (open-sourced by Spotify) — reference IDP frontend:
  - **Software Catalog**: single registry of all services/APIs/resources + ownership, defined by `catalog-info.yaml` entities (`Component`, `System`, `API`, `Resource`, `Group`, `User`, `Domain`). Answers "who owns this / what depends on what."
  - **Software Templates (Scaffolder)**: golden-path generators — pick a template, answer inputs, get a new repo + CI + infra wired up (self-service creation).
  - **TechDocs**: docs-as-code (Markdown in-repo) rendered in the portal, colocated with services.
  - **Plugins**: extensible UI surface (CI status, k8s, cost, incidents, feature flags); the ecosystem is the point.
- Backstage is a **portal/UI**, not the whole platform — the actual provisioning/automation lives behind it.

## DX metrics (measure the platform)
- **DORA**: deployment frequency, lead time for changes, change failure rate, MTTR (time-to-restore). Flow + stability.
- **SPACE** framework: Satisfaction, Performance, Activity, Communication, Efficiency — broader than DORA, includes developer sentiment.
- **DevEx**: feedback loops (fast/slow), cognitive load, flow state.
- Track adoption (% teams on golden paths), time-to-first-deploy for a new service, onboarding time, and toil reduction. Developer surveys matter as much as system metrics.

## Platform capabilities (what an IDP bundles)
- **Application/dev control plane**: scaffolding, service catalog, portal, golden-path templates (Backstage-style).
- **Integration & delivery**: CI/CD, artifact registries, GitOps (Argo CD/Flux), progressive delivery (canary/blue-green).
- **Environment/infra orchestration**: IaC + control planes (Crossplane, Terraform, Kubernetes) exposing intent-based, self-service provisioning of clusters, DBs, queues.
- **Resource/monitoring plane**: observability, cost visibility, security/policy-as-code, secrets management — wired in by default via the golden path.
- The platform's value is **composition + sane defaults + self-service**, not any single tool.

## Scorecards & standards
- **Scorecards / maturity checks** (in Backstage or similar): score each service against standards — has on-call, SLOs defined, tests, up-to-date deps, no criticals, ownership set. Drives quality without hard gates; nudges via visibility.
- Encode "production readiness" as automated checks tied to the catalog; teams see and close their own gaps.

## Control planes & APIs
- Modern IDPs expose a **platform API / control plane**: developers declare intent (a `Database` claim, a `Service` manifest) and controllers reconcile it to real infra (Crossplane compositions, operators). Declarative + self-healing beats imperative scripts.
- The portal/CLI is a thin client over that API; automation, not humans, does the provisioning.

## vs DevOps / SRE
- **DevOps** = culture/practices bridging dev + ops (shared ownership, automation). Platform engineering is one *productized* implementation of DevOps at scale — it packages the "you build it, you run it" capabilities so teams don't each reinvent them.
- **SRE** = reliability engineering discipline (SLOs, error budgets, toil reduction) for running services. Complementary: SRE defines reliability practice; the platform ships those practices as reusable, self-service defaults. Platform ≠ a rebranded ops/infra team taking tickets.

## Adoption & rollout
- Land-and-expand: pick one high-pain golden path + a friendly early-adopter team, deliver a real win, publicize it, then expand. Adoption is a marketing + trust problem, not just an engineering one.
- **Internal developer advocacy**: office hours, onboarding docs, demos, changelogs, a support channel. A platform with no relationship to its users decays.
- Version + deprecate deliberately: golden paths and templates are contracts — communicate breaking changes, provide migration paths, avoid silent churn.
- Fund via demonstrated outcomes (reduced lead time, faster onboarding), not headcount politics; tie the roadmap to developer-reported friction.

## When it's worth it
- Payoff scales with **many teams** repeatedly solving the same infra problems, high cognitive load, inconsistent practices, and slow onboarding. A handful of engineers rarely need a platform team — start with a TVP.
- Signals you're ready: copy-pasted pipelines everywhere, snowflake infra, week-long onboarding, "how do I deploy?" asked constantly, and reliability inconsistent across teams.
- Anti-signal: a small org where a shared repo of scripts + docs (the TVP) already covers the need — don't stand up a platform team prematurely.

## Pitfalls -> Fix
- **Building a platform nobody uses** (ivory-tower, no user research) -> treat as a product: interview devs, ship a thin slice for a real pain, iterate on feedback, measure adoption.
- **Gold-plating / over-engineering** (huge platform before demand) -> Thinnest Viable Platform; add capabilities only when real usage justifies them.
- **Mandating instead of enabling** (forcing teams onto the path by decree) -> win adoption by being better/faster; use guardrails + great DX, reserve hard gates for genuine safety/compliance.
- **Platform team as gatekeeper** (all infra changes route through a ticket queue) -> shift to self-service; the team builds capabilities, not approvals; unblock, don't bottleneck.
- **Ignoring DX** (powerful but painful to use, bad docs) -> invest in docs, golden-path ergonomics, fast feedback loops, and support; measure satisfaction.
- **Leaky abstractions** (self-service that still needs deep Terraform/k8s knowledge) -> abstract at the right level; expose intent-based APIs with escape hatches, not raw infra.
- **One-size-fits-all path that fits no one** -> golden paths per common service archetype; allow off-road with clear ownership of the extra work.
- **Rebranding ops as "platform"** without the product mindset -> productize: roadmap, versioning, changelogs, deprecation policy, internal marketing, customer support.
- **No metrics** (can't prove value, funding at risk) -> instrument DORA/SPACE + adoption + time-to-deploy; report outcomes to leadership.
- **Catalog rot** (Backstage entities stale/incomplete) -> automate entity discovery/registration in CI; enforce ownership; make the catalog authoritative, not manual.
- **Platform becomes a monolith bottleneck** (one team owns everything, can't keep up) -> federate: platform provides paved roads + guardrails, stream teams self-serve within them.
- **Confusing platform with SRE/DevOps team** (dumping all reliability + tickets on them) -> keep the product boundary: reusable self-service capabilities, not a catch-all ops group.
