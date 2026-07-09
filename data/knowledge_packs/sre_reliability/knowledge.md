# SRE and Reliability Engineering

## SLI / SLO / SLA
- SLI (Indicator): a measured ratio of good events to valid events. `SLI = good / valid`. E.g. `(non-5xx responses) / (total responses)`, or `(requests < 300ms) / total`. Measure at the user-facing edge.
- SLO (Objective): internal target for an SLI over a window. E.g. "99.9% of requests succeed over rolling 28 days", "p99 latency < 300ms". Drives engineering decisions.
- SLA (Agreement): external contract with consequences (refunds/credits) if breached. Always set SLO stricter than SLA (SLO ≈ SLA + margin) so you react before contract breach.
- Pick 1-3 SLIs per user journey; categories: availability, latency, correctness, freshness, throughput, durability. Fewer, meaningful SLIs beat many vanity metrics.

## Error budgets
- Error budget = `1 - SLO`. 99.9% SLO over 28 days → 0.1% = ~40.3 min unavailability allowed/month; 99.99% → ~4.3 min/month; 99% → ~7.3 hr.
- Budget is a shared currency: spend it on feature velocity, risky deploys, experiments. Reliability and velocity trade against one budget.
- Burn rate = how fast you consume budget vs steady. Burn rate 1 exhausts budget exactly at window end; 14.4 exhausts a 30-day budget in ~2 days. Alert on multi-window burn (e.g. 2% budget in 1h AND 5m confirming).
- Error budget policy (write it down, agree in advance): budget remaining → ship features; budget exhausted → freeze feature launches, all hands to reliability until back in budget. Escalation path + who signs off. Policy is the point; SLOs without a policy are decoration.

## Toil reduction
- Toil = manual, repetitive, automatable, tactical, no enduring value, scales linearly with load (restarts, manual failovers, ticket-driven provisioning). NOT overhead (meetings, email).
- Cap toil at <50% of SRE time; excess is a reliability + retention risk. Track it explicitly.
- Automate the frequent + risky first. Progression: document → script → self-service → fully automated with guardrails. ROI: automate if `time_saved_per_run * frequency > build+maintain cost`.

## Incident management
- Severity (tune to org): SEV1 = major outage / data loss / revenue impact, all-hands; SEV2 = significant degradation, urgent; SEV3 = minor/partial, business hours. Define objectively.
- Roles: Incident Commander (IC) — owns coordination + decisions, does NOT debug; Ops/tech lead — hands on the system; Comms lead — stakeholder/status-page updates; Scribe — timeline. One IC at a time; IC delegates.
- Flow: detect → declare (don't hesitate) → dedicated channel/bridge → mitigate first (restore service; rollback > root-cause fix during incident) → communicate on cadence → resolve → postmortem.
- Comms: regular status even when "no update"; internal + external (status page) separate; avoid speculation. MTTA/MTTR start at detect.

## On-call + runbooks
- Sustainable rotation: ≥ 6-8 people, follow-the-sun for global; compensated; hard cap on pages/shift (Google target ≤ 2 incidents/shift) so responders can act deliberately.
- Every alert links to a runbook: symptoms, dashboards, diagnosis steps, mitigation, escalation contacts, rollback command. Runbook must let a non-expert act.
- Primary/secondary escalation; auto-escalate on no-ack timeout (PagerDuty/Opsgenie). Handoff notes between shifts.

## Blameless postmortems
- Blameless: assume everyone acted reasonably with the info they had. Target systems/processes, not people — fear hides truth and kills learning.
- Trigger on defined threshold (any SEV1/2, SLO breach, near-miss). Contents: summary, impact (users/duration/revenue), timeline (UTC), root cause(s), detection, resolution, what went well / poorly / got lucky, action items.
- Action items: each has an owner, due date, tracked ticket, priority; prefer systemic fixes (add guardrail, remove footgun) over "be more careful". Review completion — un-actioned postmortems repeat incidents.
- Use 5 Whys / causal analysis; expect multiple contributing causes, not one root cause.

## Chaos engineering
- Deliberately inject failure to find weaknesses before they page you. Steady-state hypothesis → inject (kill pod, add latency, drop deps, exhaust CPU) → verify hypothesis holds → learn.
- Start in staging, small blast radius, business hours, with abort/rollback. Graduate to prod GameDays. Tools: Chaos Mesh, Gremlin, Litmus, AWS FIS, Toxiproxy.
- Tests: dependency failure, region/AZ loss, latency injection, resource exhaustion, DNS/cert failure. Validates graceful degradation + runbooks are real.

## Capacity planning
- Provision for peak + headroom (e.g. N+2, or run at ≤ 60-70% steady so a spike/instance-loss doesn't saturate). Model organic growth + launches + seasonality.
- Load test to find the knee (where latency degrades non-linearly). Track saturation SLIs (queue depth, pool exhaustion, CPU run-queue). Autoscale on leading signals; keep min floor for cold-start.
- Distinguish resource limits from quota limits; watch both. Plan lead time for hardware/quota approvals.

## Reliability patterns
- Graceful degradation: shed non-critical features to keep core alive (serve stale cache, hide recommendations) rather than fail whole page.
- Load shedding: reject excess load early (429) to protect the system from collapse; prioritize by request class. Better to serve 90% well than 100% badly.
- Backpressure: propagate "slow down" upstream (bounded queues, blocking, credits) instead of unbounded buffering → OOM.
- Circuit breaker: after N failures, open circuit, fail fast, periodically half-open to probe recovery. Timeouts on every network call; retries with exponential backoff + jitter + budget (retries amplify overload — cap them). Bulkheads isolate resource pools so one dependency can't starve all.
- Idempotency keys for safe retries; hedged requests for tail latency.

## Reliability metrics
- MTBF = mean time between failures (higher better). MTTR = mean time to recovery (lower better). MTTD = detect, MTTA = acknowledge. Availability ≈ `MTBF / (MTBF + MTTR)`.
- Improving MTTR (faster detect + rollback) often beats chasing MTBF (preventing every failure). Track trends, not single incidents.
- Availability "nines": 99% = 3.65 d/yr down; 99.9% = 8.77 h/yr; 99.95% = 4.38 h/yr; 99.99% = 52.6 min/yr; 99.999% = 5.26 min/yr. Each nine ~10× cost. Compound dependencies multiply: three 99.9% serial deps → ~99.7%.
- DORA metrics (delivery health, correlate with reliability): deploy frequency, lead time for change, change failure rate, time to restore. Elite: multiple deploys/day, <1h lead, <15% CFR, <1h restore.

## Reliability review + design
- Production readiness review (PRR) before launch: SLOs defined, dashboards + alerts wired, runbooks written, load-tested, rollback tested, on-call staffed, dependencies mapped with fallbacks.
- Map hard vs soft dependencies: a hard dep down = you're down (minimize these); soft dep down = degrade gracefully. Eliminate single points of failure; prefer redundancy across AZ/region.
- Design for failure: assume every network call fails/times out; every dependency degrades; every instance dies. Timeouts + retries + fallbacks on all of them.

## Gotchas -> Fix
- Chasing 100% uptime -> impossible + infinitely expensive; set a realistic SLO (99.9/99.95), keep an error budget, spend it deliberately.
- SLOs defined but no error budget policy -> nobody changes behavior; write policy with agreed consequences (feature freeze on exhaustion) before you need it.
- Alerting on causes (CPU, single pod, disk) -> page on SLO burn / user-visible symptoms; make cause metrics runbook context.
- Hero/blame culture, one person firefights everything -> spread on-call, blameless postmortems, cap pages/shift, share runbooks; heroes = a bus-factor + burnout risk.
- Retry storms amplify an outage -> exponential backoff + jitter, retry budgets, circuit breakers, load shedding.
- Postmortems written, action items never done -> owner+due+ticket per item, track completion, prioritize systemic fixes; else incidents recur.
- Toil grows until no time for engineering -> measure toil, cap <50%, automate frequent/risky first.
- SLO = SLA (or looser) -> set SLO stricter than SLA so you react before contract penalties.
- No incident commander, everyone debugging + nobody coordinating -> declare early, assign single IC who coordinates (not debugs), separate comms role.
- Unbounded queues/buffers under overload -> OOM; add backpressure + bounded queues + load shedding.
- Alert flapping / on-call burnout -> `for:` durations, multi-window burn-rate alerts, delete non-actionable alerts, measure pages/shift.
- Capacity at 95% "to save cost" -> one spike/instance loss cascades; run ≤ 60-70% with N+2 headroom.
- Fixing root cause live instead of mitigating -> mitigate first (rollback/failover) to stop bleeding; root-cause in postmortem.
