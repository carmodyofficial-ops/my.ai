# Chaos Engineering

## Principles
- Discipline of **experimenting on a system** to build confidence in its ability to withstand turbulent conditions in production. Goal = find weaknesses **before** they cause outages.
- Core method (Principles of Chaos):
  1. Define **steady state** = a measurable output that signals normal (e.g. p99 latency, orders/sec, error rate) — NOT internal metrics like CPU. This is your hypothesis's yardstick.
  2. **Hypothesize** steady state continues in both control and experimental groups.
  3. **Inject real-world faults** (dependency down, latency, instance loss, region failure).
  4. **Disprove** the hypothesis: if steady state diverges, you found a weakness.
- **Minimize blast radius**: smallest experiment that yields signal; start tiny, expand as confidence grows.
- **Run in production** (carefully) — staging can't reproduce real traffic, scale, data, and dependencies. But earn it: prove it in staging first, have an abort.
- It is **planned, controlled experimentation**, not random breakage. Every experiment has a hypothesis, scope, abort condition, and observers.

## Experiments (fault types)
- **Kill/terminate**: pod/node deletion, process kill, container restart (baseline resilience: does it self-heal?).
- **Latency injection**: add delay to a dependency/network path (find missing timeouts, retry storms, cascading slowdowns).
- **Fault/error injection**: return 5xx/errors from a dependency, drop a percentage of requests (validate fallbacks/circuit breakers).
- **Network**: partition (split-brain), packet loss, DNS failure, bandwidth throttle, blackhole a dependency.
- **Resource exhaustion**: CPU/memory/disk pressure, fill disk, exhaust file descriptors/connection pools (find OOM behavior, limits).
- **Clock skew**, dependency failure (DB/cache/queue down), **zone/region failure** (biggest test: does failover actually work?).
- **Time-based**: expire certs/tokens, leap conditions.

## Tools
- **Chaos Mesh** (CNCF, k8s): CRDs `PodChaos`, `NetworkChaos`, `StressChaos`, `IOChaos`, `TimeChaos`, `HTTPChaos`, `DNSChaos`; `Schedule` + `Workflow` for orchestration; dashboard. Selectors scope blast radius by label/namespace.
- **LitmusChaos** (CNCF, k8s): `ChaosEngine`/`ChaosExperiment`, hub of experiments, GitOps-friendly, probes as SLO checks.
- **Gremlin**: commercial SaaS, "attacks" (resource/state/network), built-in halt/blast-radius controls, Status Checks (auto-abort), Scenarios.
- **AWS FIS** (Fault Injection Service): managed, integrates with CloudWatch alarms as **stop conditions**; SSM for host-level actions.
- **Netflix Chaos Monkey / Simian Army** (origin), **Toxiproxy** (TCP fault proxy for latency/partition in tests), **Pumba** (Docker), **kube-monkey**.

## Game days & process
- **Game day**: scheduled, cross-team exercise where a known fault is injected and the team practices detection + response (tests runbooks, alerting, on-call, and human coordination — not just the system).
- Structure: hypothesis + scope written up front, announce (or intentionally don't, for a true test), assign observers, define abort criteria, run, measure vs steady state, **blameless retro** -> action items.

## Prerequisites & maturity
- **Observability is mandatory** — you cannot run chaos safely without metrics/tracing/logging to see the steady state and detect impact. No dashboard = no experiment.
- Working alerting + on-call + runbooks; automated **rollback/abort** (halt button); ability to scope blast radius (feature flags, canary, cell/zone routing).
- Links to **SLOs / error budgets**: chaos spends error budget deliberately; run when budget allows, and use experiments to validate the reliability the budget assumes.

## Progressive rollout
- Maturity ladder: **dev -> staging -> prod**; within prod: single instance -> small % -> one cell/zone -> region. Expand blast radius only after each level passes.
- **Automate chaos**: move from manual game days to continuous, scheduled experiments in CI/CD and prod (with auto-abort) so regressions in resilience are caught continuously, not once a year.

## Designing an experiment (template)
- **Hypothesis**: "If `payment-svc` loses its primary DB replica, checkout success rate stays > 99% via failover within 30s."
- **Steady state**: checkout success rate (SLI) and p99 latency, measured on a dashboard.
- **Scope/blast radius**: one AZ, 5% of traffic, staging first; selectors target only `payment-svc` DB.
- **Abort/stop condition**: success rate < 98% for 60s -> auto-halt; hard time-box `duration: 5m`.
- **Method**: inject fault, hold, observe control vs experiment group, measure MTTR, restore.
- **Outcome**: pass (confidence gained) or fail (weakness + action item, ticketed, owned).

## Chaos Mesh example (scoped, time-boxed)
```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata: { name: db-latency }
spec:
  action: delay
  mode: one                # one pod only = small blast radius
  selector: { namespaces: [payments], labelSelectors: { app: db } }
  delay: { latency: "200ms", jitter: "50ms" }
  duration: "5m"           # auto-recovers
```
- `mode: one|fixed=N|percent=25` bounds blast radius; `duration` guarantees auto-recovery; `Schedule` CR runs it recurringly; `Workflow` sequences multi-stage experiments with conditions.

## Metrics that matter
- Track: SLI deviation during injection, time-to-detect (alert fired?), time-to-recover (MTTR), whether runbooks worked, and any collateral (dependencies affected). Feed findings back into SLOs, alerting thresholds, and capacity.
- Resilience patterns validated by chaos: timeouts, retries with backoff+jitter, circuit breakers, bulkheads, graceful degradation/fallbacks, autoscaling, multi-AZ/region failover, health checks + readiness gating.

## Gotchas -> Fix
- **No defined steady-state metric** -> you can't tell if the experiment caused harm -> define a measurable business/user-facing SLI (latency, success rate) BEFORE injecting; abort if it deviates.
- **Blast radius too large** -> an experiment becomes a real outage -> start with the smallest scope (one pod, 1% traffic, non-critical path), tight selectors, low percentages; expand only after clean runs.
- **No abort / rollback** -> can't stop a runaway experiment -> require an automated halt and a **stop condition** (CloudWatch alarm/Gremlin Status Check/Chaos Mesh duration+pause); time-box every experiment (`duration`).
- **Chaos without observability** -> you inject faults but can't see the effect -> instrument first; wire experiment start/stop as annotations on dashboards to correlate.
- **One-off instead of continuous** -> resilience regresses silently after a single game day -> schedule recurring, automated experiments (Chaos Mesh `Schedule`, CI gates).
- **Running in prod before staging** -> unknown-unknowns hit customers first -> validate the mechanism + tooling in staging, THEN prod with minimal scope.
- **Blaming individuals** -> people hide failures, learning stops -> blameless retros; the target is the system/process, and findings become action items with owners.
- **Injecting faults the system already can't survive with no plan** -> guaranteed customer impact for no new insight -> hypothesize a *specific* weakness; if you're confident it'll fail, fix it first.
- **Ignoring dependencies' blast radius** -> killing a shared dependency (DNS, auth, a shared DB) cascades far beyond the target -> map the dependency graph; scope to your service's copy, use fault-proxies (Toxiproxy) to isolate.
- **Experiment during an active incident or low error budget** -> compounds real problems -> gate experiments on healthy SLOs / remaining error budget; freeze during incidents and change freezes.
- **Testing failure but not recovery** -> the fault is injected but you never verify self-heal/failover completed -> include recovery in the hypothesis and measure time-to-recover (MTTR).
- **No communication** -> on-call pages, another team panics -> announce scheduled experiments, tag alerts, use a shared calendar; for "surprise" tests limit to a trusted small group.
- **Control vs experiment group not isolated** -> shared caches/DBs/queues mean the "control" is also affected -> route via cells/canary so the blast radius is truly partitioned; compare a genuinely unaffected baseline.
- **Chaos tooling itself has blast radius** -> a broad selector (`mode: all` / missing namespace filter) hits far more than intended -> always scope with tight label/namespace selectors and `mode: one|percent`, dry-run the selector, review before apply.
- **Cleanup fails, fault persists** -> injector crashes mid-experiment leaving latency/partition in place -> always set `duration` for auto-recovery, verify teardown, keep a manual `kubectl delete <chaos-cr>` / `flush` runbook.
- **Findings never actioned** -> same weakness resurfaces -> every failed experiment produces a tracked, owned remediation; re-run the experiment to confirm the fix (regression test for resilience).
- **Measuring the wrong thing** -> infra metric (CPU) used as steady state instead of user-facing SLI -> anchor the hypothesis to a customer-visible signal (success rate, latency, throughput).
- **Skipping the abort drill** -> the halt button was never tested and fails when needed -> rehearse aborts; treat the stop mechanism as a first-class, tested control.
