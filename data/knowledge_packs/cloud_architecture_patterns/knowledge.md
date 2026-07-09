# Cloud Architecture Patterns

## Well-Architected pillars
- **Operational excellence**: run + evolve — IaC, small reversible changes, runbooks, observability, game days, post-incident learning.
- **Security**: least privilege, defense in depth, encrypt everywhere, traceability (audit logs), automate guardrails.
- **Reliability**: recover from failure automatically, scale horizontally, test recovery (DR drills), design for failure not hope.
- **Performance efficiency**: right resource for the job, serverless/managed where it fits, measure + iterate, use caching/CDN.
- **Cost optimization**: pay for what you use, right-size, use spot/reserved/savings plans, tiered storage, kill idle, attribute cost (tags).
- **Sustainability**: minimize provisioned resources, use managed/serverless (higher utilization), right-size, pick efficient regions, delete unused data.
- Tension: reliability/performance cost money; cost pressure erodes resilience. Make trade-offs explicit per workload tier.

## High availability
- Eliminate single points of failure. Redundancy at every layer: multiple instances behind a load balancer, replicated DBs, multiple paths.
- **Multi-AZ**: deploy across ≥2–3 Availability Zones (independent power/network/cooling in a region). Survives one AZ failure with no data loss (sync replication). Standard baseline for prod.
- **Multi-region**: survives a whole-region outage; needed for strict availability SLAs or geo latency. Costs more, adds cross-region latency + data-consistency complexity + data-residency concerns.
- Availability math: components in series multiply (99.9% x 99.9% ≈ 99.8%); redundancy in parallel raises it. Adding nines gets exponentially expensive.
- Health checks + auto-replacement (ASG/managed instance groups); load balancer removes unhealthy targets.

## Disaster recovery (RTO/RPO)
- **RTO** = max tolerable time to restore service. **RPO** = max tolerable data loss (time). Drive strategy + cost.
- Strategies (cheap/slow -> expensive/fast):
  - **Backup & restore**: backups in another region; rebuild on disaster. RTO hours, RPO hours. Cheapest.
  - **Pilot light**: core (DB replicated, AMIs ready) always on but scaled to minimum; spin up the rest on failover. RTO ~10s of min.
  - **Warm standby**: scaled-down full copy always running; scale up on failover. RTO minutes.
  - **Active-active (multi-site)**: full capacity in ≥2 regions serving traffic; failover is routing. RTO near-zero, RPO near-zero. Most expensive + hardest (data sync/conflict).
- **Test DR regularly** — untested backups/failover are assumptions, not capabilities. Automate failover + failback; watch for asymmetric failback.
- Backups: encrypted, versioned, cross-region/cross-account, immutability/object-lock against ransomware, tested restores.

## Scalability
- **Horizontal** (add instances) beats **vertical** (bigger box): no ceiling, no single point of failure, cheaper commodity nodes. Requires **stateless** app tier (state in DB/cache/session store) so any instance handles any request.
- **Auto-scaling**: target-tracking (keep CPU/RPS at target), step, scheduled (known peaks), predictive. Scale out fast, in slow (avoid flapping). Set sane min/max.
- Decouple with queues (SQS/Kafka) to absorb spikes; consumers scale on queue depth (backpressure).
- Scale the data tier too: read replicas, sharding/partitioning, caching, CQRS. The DB is the usual bottleneck.
- Load balancing: L7 (ALB, path/host routing) vs L4 (NLB, raw TCP, ultra-low latency); global via DNS/anycast (Route 53, Global Accelerator, CDN).

## Resilience patterns
- **Retry with exponential backoff + jitter**: retry transient failures; jitter prevents synchronized retry storms. Cap attempts; only retry idempotent ops.
- **Circuit breaker**: after N failures, "open" and fail fast (stop hammering a dead dependency); "half-open" probes for recovery. Prevents cascading failure + resource exhaustion.
- **Bulkhead**: isolate resources (separate connection pools/thread pools/queues per dependency) so one saturated dependency can't sink everything.
- **Timeouts everywhere**: no unbounded waits; a slow dependency without a timeout exhausts your threads/connections.
- **Graceful degradation**: shed non-essential features, serve stale cache, return partial results when a dependency is down — degrade, don't collapse.
- **Rate limiting / throttling / load shedding**: protect yourself and downstreams; reject excess early.
- **Idempotency + dedup**: safe retries. **Health checks + self-healing**: auto-replace bad nodes.

## Caching layers
- **CDN/edge** (CloudFront, Cloudflare): static assets + cacheable API responses near users; offloads origin, cuts latency.
- **In-memory app cache** (Redis/Memcached): hot data, sessions, computed results. Distributed so it survives instance churn.
- **DB query/read-replica cache**; **client/browser cache** via Cache-Control/ETag.
- Invalidation is the hard part: TTLs, write-through/write-around/write-back, cache-aside (lazy load on miss). Guard against **stampede** (lock/single-flight on miss) and **stale reads**.

## Cost optimization
- **Right-size**: match instance/memory to actual utilization (metrics, not guesses); downsize idle.
- **Purchasing**: Spot (up to ~90% off, interruptible — fault-tolerant/batch/stateless), Reserved Instances / Savings Plans (steady baseline, 1–3 yr commit), On-demand (spiky/unknown). Blend: reserved baseline + spot for burst.
- **Storage tiers**: hot -> infrequent-access -> archive/Glacier via lifecycle policies; delete orphaned volumes/snapshots/old logs.
- Turn off non-prod off-hours; scale-to-zero serverless for spiky; managed services to cut ops cost.
- **Cost visibility**: tag everything, per-team/service allocation, budgets + anomaly alerts. Watch hidden costs: NAT gateway, cross-AZ/region data transfer, idle load balancers, over-provisioned logging.

## Security
- **Least privilege**: minimal IAM per identity/role, scoped, time-bound; no wildcard admin; roles not long-lived keys; short-lived creds (OIDC/STS).
- **Defense in depth**: layered — network (VPC, subnets, security groups, NACLs, private subnets, WAF), identity, app, data. No single control is trusted alone.
- **Encryption**: at rest (KMS-managed keys, rotate) + in transit (TLS everywhere, mTLS internal). Manage keys/secrets in a vault (Secrets Manager/KMS), never in code/env-plaintext.
- Private by default: no public S3/DB; access via private endpoints/PrivateLink; bastion/SSM instead of open SSH.
- Audit + detect: CloudTrail/audit logs, config drift detection, GuardDuty/threat detection, centralized logging, immutable log store.
- Automated guardrails: SCPs/org policies, policy-as-code (OPA), block public access org-wide.

## Landing zones & multi-account
- **Multi-account** (AWS Organizations / GCP folders / Azure management groups): isolate blast radius, billing, and security boundaries — separate accounts per env (prod/stage/dev) and per team/workload.
- **Landing zone**: pre-baked, governed multi-account baseline — centralized identity (SSO), logging, networking (transit gateway/hub-spoke), guardrails (SCPs), and account vending. Control Tower / Landing Zone Accelerator.
- Benefits: strong isolation, least-privilege at account granularity, clear cost attribution, limits blast radius of a compromise.

## Data & consistency
- **CAP**: under a network partition you choose availability or consistency. Multi-region writes force this — pick per workload (CP for money/inventory, AP for feeds/carts).
- Consistency models: strong (linearizable, higher latency) vs eventual (fast, replicas lag) vs read-your-writes/monotonic. Match to the business rule, not habit.
- **Idempotency + sagas** for distributed transactions: no cross-service 2PC — use a saga (sequence of local txns + compensating actions) or an event log with outbox pattern to avoid dual-write inconsistency.
- Partition/shard for scale; replicate for availability; separate read (replicas/CQRS) from write. Backpressure + queues smooth spikes into the data tier.

## Observability & operations
- Three pillars: **metrics** (rates/latency/errors — RED/USE method), **logs** (structured, centralized, correlated by trace ID), **traces** (distributed request path across services).
- SLI/SLO/error budgets drive reliability spend; alert on symptoms (user-facing SLO burn) not causes; page only on actionable, urgent conditions.
- Deploy safely: blue/green, canary, feature flags, automated rollback on health regression. IaC + immutable infrastructure (replace, don't patch in place).

## Gotchas -> Fix
- **Single-AZ prod**: one AZ outage = full downtime. Fix: multi-AZ, LB across AZs, cross-AZ DB replica.
- **Untested DR**: backups never restored, failover never drilled. Fix: scheduled DR game days; automate + measure actual RTO/RPO vs targets.
- **Stateful app tier blocks scaling**: sticky in-memory sessions -> can't add/remove nodes freely. Fix: externalize state (Redis/DB); stateless instances.
- **Retry storm / cascading failure**: naive retries amplify an outage. Fix: backoff+jitter, circuit breaker, bulkheads, timeouts, load shedding.
- **No timeouts**: slow dependency exhausts threads/connections -> total collapse. Fix: aggressive timeouts + circuit breaker on every remote call.
- **Cache stampede**: TTL expiry -> thundering herd rebuilds hot key. Fix: single-flight lock, staggered TTLs, serve-stale-while-revalidate.
- **Cost blowup from data transfer**: cross-AZ/region + NAT + egress dwarf compute. Fix: co-locate chatty services, VPC endpoints instead of NAT, CDN for egress, monitor transfer.
- **Over-provisioned "just in case"**: idle capacity burns money. Fix: right-size on metrics, auto-scale, spot/reserved mix, scale-to-zero non-prod.
- **Over-permissive IAM (`*:*`)**: one leaked cred = full compromise. Fix: least privilege, scoped roles, short-lived creds, access analyzer.
- **Public data store**: open S3/DB = breach. Fix: block-public-access org-wide, private subnets/endpoints, encryption + audit.
- **Multi-region added blindly**: 2x cost + consistency bugs for a workload that only needs multi-AZ. Fix: match DR tier to actual RTO/RPO/SLA; most workloads are fine multi-AZ.
- **Single account, everything shared**: one mistake nukes prod, no cost attribution. Fix: multi-account landing zone, env/team isolation, SCP guardrails.
- **Encryption/keys as afterthought**: unencrypted volumes, keys in code. Fix: enforce encryption via policy, KMS + rotation, secrets vault.
