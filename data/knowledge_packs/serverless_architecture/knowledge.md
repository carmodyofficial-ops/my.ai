# Serverless Architecture

## FaaS model
- Functions are **stateless, event-driven, ephemeral**: no local state survives between invocations, no long-lived server you manage. Provider handles provisioning, scaling to zero, patching.
- One invocation = one event -> one function execution in an isolated container/microVM. Concurrency scales by running many isolated instances in parallel (not threads in one process).
- Bill per invocation + GB-seconds (memory x duration). Idle = $0. CPU scales with memory allocation (AWS Lambda: more MB -> more vCPU).
- Trade managed ops + granular scaling for cold starts, execution limits, and stateless constraints.

## Triggers / event sources
- **HTTP/sync**: API Gateway / ALB / Function URL -> request/response, client waits. Latency-sensitive; cold start visible to user.
- **Queue/async**: SQS, EventBridge, Pub/Sub -> buffered, provider retries, natural backpressure. Use for work that can be decoupled.
- **Schedule**: cron (EventBridge Scheduler / Cloud Scheduler) -> periodic jobs.
- **Stream**: Kinesis, DynamoDB Streams, Kafka -> ordered per-shard batch processing, checkpointing; poll-based.
- **Storage/event**: S3 put, blob created -> reactive pipelines.
- Invocation type matters: **sync** returns to caller (no built-in retry); **async** provider retries (2x by default on Lambda) then DLQ; **poll/stream** retries the whole batch until success or expiry.

## Cold starts
- Cause: no warm instance available -> provider must init a new execution environment: download/mount code, start runtime, run init/global code, then handler. Adds ~100ms–several seconds.
- Worse with: large deployment packages, heavy dependency trees, JVM/.NET runtimes, VPC-attached functions (ENI/network setup — much improved but still real), lots of top-level init work.
- Mitigations:
  - **Provisioned concurrency** (Lambda) / **minimum instances** (Cloud Run/Functions) — pre-warmed, no cold start, but you pay for idle. Best for latency-critical sync APIs.
  - Shrink package: tree-shake, drop unused SDK modules, use layers, smaller base images.
  - Faster runtime: Node/Python/Go start faster than JVM/.NET; consider SnapStart (Java) / AOT.
  - Move heavy init to **global/module scope** so it's reused across warm invocations (DB clients, SDK clients) — but init still counts in cold start.
  - Right-size memory up: more memory = more CPU = faster init + execution (often cheaper net).
- "Keep-warm" pings are a crude hack; provisioned concurrency is the real fix.

## Statelessness & external state
- No reliable local disk (`/tmp` is ephemeral, not shared across instances, may persist on warm reuse — never rely on it). No in-process session/cache shared across concurrent instances.
- Externalize all state: DynamoDB/Firestore (KV/doc), RDS/Cloud SQL (relational), S3/GCS (blobs), ElastiCache/Redis (shared cache, sessions).
- Config via env vars + secrets manager (fetch once at init, cache in global scope).

## API Gateway patterns
- REST/HTTP API in front of functions: routing, auth (JWT/Cognito/Lambda authorizers), throttling, request/response mapping, WAF.
- Proxy integration passes the whole request to one function (function does routing) vs per-route function (one function per method+path — better isolation, more cold-start surface).
- Usage plans + API keys for rate limiting per client; caching at the gateway for GETs.
- HTTP API (AWS) is cheaper/faster than REST API; use REST API only for features it lacks (request validation, WAF-on-stage, edge-optimized).

## Orchestration
- Chaining functions by having each invoke the next -> brittle, no visibility, tight coupling. Use an orchestrator.
- **Step Functions (AWS)** / **Durable Functions (Azure)** / **Workflows (GCP)**: define state machines/workflows with retries, error handling, parallelism, wait states, human approval, and built-in observability.
  - Express workflows (high-volume, ≤5 min, at-least-once) vs Standard (long-running up to 1 yr, exactly-once, full audit).
- **Fan-out/fan-in**: split work across many parallel function invocations (fan-out via SNS/EventBridge/Map state), aggregate results (fan-in). Map state or a queue + aggregator. Watch downstream concurrency limits when fanning out.
- Event choreography (each service reacts to events) vs orchestration (central coordinator) — choreography scales/decouples better, orchestration gives visibility/control.

## Idempotency, retries, DLQs
- Async + stream sources retry -> **at-least-once delivery**. Handlers MUST be idempotent: dedupe on an idempotency key (message ID / business key) stored in DynamoDB/Redis with a conditional put.
- Retries with backoff on transient failures; distinguish retriable (throttle, timeout) from poison (bad payload) errors — don't retry poison.
- **DLQ** (SQS/SNS) captures messages that exhaust retries -> inspect, fix, replay. Without a DLQ, failed async events are silently dropped.
- Stream sources block the shard on a failing batch (head-of-line blocking) — configure bisect-on-error, max retry age, and an on-failure destination.

## Limits (know these)
- **Timeout**: Lambda 15 min max; API Gateway caps sync at 29–30s regardless of function timeout. Cloud Run 60 min. Long jobs -> async/Step Functions.
- **Memory**: Lambda 128MB–10GB (CPU scales with it).
- **Payload**: Lambda sync 6MB, async 256KB; API Gateway 10MB. Large data -> S3 + pass a pointer.
- **Concurrency**: account/region cap (default Lambda 1000, adjustable); per-function reserved concurrency to protect others; provisioned for pre-warm.
- **Deployment package**: 50MB zipped / 250MB unzipped (layers included); container image up to 10GB.
- `/tmp`: 512MB default, up to 10GB configurable.

## Observability & cost
- Structured JSON logs -> CloudWatch/Cloud Logging; distributed tracing (X-Ray / OpenTelemetry) to see cross-function latency and cold starts.
- Key metrics: invocations, errors, throttles, duration (p50/p99), concurrent executions, cold-start count, DLQ depth.
- Cost = requests + GB-s. Cheap at low/spiky volume; can exceed always-on containers at high sustained volume. Model it. Right-size memory (faster+cheaper sweet spot exists). Watch API Gateway + data transfer + downstream (a Lambda hammering RDS/NAT costs more than the Lambda).

## Serverless vs containers
- **Serverless when**: spiky/unpredictable/low-baseline traffic, event-driven glue, want scale-to-zero + minimal ops, short tasks.
- **Containers (Fargate/Cloud Run/K8s) when**: steady high throughput, long-running/streaming, large images or GPUs, need full control over runtime/networking, WebSocket-heavy, cost at scale. Cloud Run blurs the line (scale-to-zero containers).

## Packaging, deployment, versioning
- Package as zip (fast cold start, size-limited) or container image (up to 10GB, custom runtimes, portable). Shared code/deps go in **layers** (Lambda) to slim the function and speed deploys.
- **Aliases + versions**: publish immutable numbered versions; point an alias (`prod`, `staging`) at one. Shift traffic gradually (weighted alias / canary) and roll back by repointing the alias — no redeploy.
- Least-privilege execution role per function (scope to exactly the resources it touches). Reserved concurrency both caps a function and guarantees it capacity, protecting neighbors from a runaway function.
- Warm-instance reuse: code outside the handler runs once per cold start and is reused — initialize SDK/DB clients, load config, and open long-lived connections there, not inside the handler.
- Local dev/test: SAM / serverless-framework / CDK for packaging + IaC; emulate events; but always integration-test against real triggers (queue/stream semantics don't emulate perfectly).

## Gotchas -> Fix
- **Cold-start latency on user-facing API**: p99 spikes. Fix: provisioned/min concurrency, smaller package, faster runtime, more memory, keep VPC-attach only if needed.
- **DB connection pool exhaustion**: each concurrent function opens its own connection -> hundreds of conns kill RDS/Postgres. Fix: RDS Proxy / Hyperdrive / PgBouncer to pool; keep max conns low; reuse client in global scope; prefer HTTP/serverless-native datastores.
- **Retry storm / thundering herd**: transient downstream failure -> mass retries amplify the outage. Fix: exponential backoff + jitter, circuit breaker, cap reserved concurrency, DLQ to shed load.
- **Non-idempotent handler + at-least-once**: duplicate side effects (double charge). Fix: idempotency key with conditional write; make writes idempotent.
- **Timeout mismatch**: API Gateway returns 504 at 29s though function keeps running (and you're billed) to 15 min. Fix: align timeouts; make long work async and return 202 + poll/webhook.
- **Silent async failures**: no DLQ -> events vanish. Fix: configure DLQ / on-failure destination; alarm on DLQ depth.
- **State in `/tmp` or globals across "users"**: warm reuse leaks data between requests or state disappears on new instance. Fix: treat every invocation as fresh; externalize state; only cache non-request-specific things globally.
- **Payload too large**: 413/errors on big bodies. Fix: upload to S3, pass a reference/presigned URL.
- **Fan-out overwhelms downstream**: 500 parallel Lambdas -> DB/API throttled. Fix: reserved concurrency, SQS with controlled batch/concurrency, backpressure.
- **Stream stuck on poison record**: one bad message blocks the shard forever. Fix: bisect-on-error, max-retry-age, on-failure destination.
- **Cost surprise at scale**: sustained high traffic on per-invocation billing beats a container fleet. Fix: benchmark; move hot always-on paths to Fargate/Cloud Run.
- **Vendor lock-in**: proprietary triggers/Step Functions ASL. Fix: keep business logic in portable handlers; isolate provider glue at the edges.
