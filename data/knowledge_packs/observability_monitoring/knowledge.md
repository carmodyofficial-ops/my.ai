# Observability and Monitoring

## Three pillars — and why they differ
- Metrics: numeric time series, cheap, aggregatable, low-cardinality. Answer "is something wrong, how much, trend". Store forever, cheap. Cannot explain a single request.
- Logs: discrete timestamped events, high detail, high volume/cost. Answer "what exactly happened in this event". Bad at aggregation/trends.
- Traces: causally-linked spans across services for one request. Answer "where in the request path is the latency/error". Best for distributed debugging; usually sampled.
- Monitoring = predefined dashboards/alerts on known-unknowns. Observability = ability to ask new questions (unknown-unknowns) without shipping new code; needs high-cardinality wide events.
- Correlate the three: exemplars link a metric bucket to a trace ID; trace ID in structured logs links logs to traces. Always propagate one `trace_id`/`request_id`.

## Metric types (Prometheus/OpenMetrics)
- Counter: monotonic, only increases (resets to 0 on restart). Requests, errors, bytes. Query with `rate()`/`increase()`, never raw value.
- Gauge: goes up/down. Queue depth, temperature, in-flight requests, memory. Use `avg`/`max`/`min`, not `rate`.
- Histogram: pre-bucketed cumulative `_bucket{le=...}` + `_sum` + `_count`. Server-side quantiles via `histogram_quantile(0.99, sum(rate(x_bucket[5m])) by (le))`. Aggregatable across instances. Bucket boundaries fixed at instrumentation time.
- Summary: client-computed quantiles (`{quantile=...}`) + `_sum`+`_count`. NOT aggregatable across instances (cannot average percentiles). Prefer histograms for multi-instance p99.

## RED and USE methods
- RED (request-driven services): Rate (req/s), Errors (failed req/s or %), Duration (latency distribution). One dashboard per service.
- USE (resources): Utilization (% busy), Saturation (queue/wait, e.g. load, run-queue), Errors (device errors). One per resource (CPU, disk, net, pool).
- Four Golden Signals (Google SRE): Latency, Traffic, Errors, Saturation. Superset of RED + saturation.
- Measure latency as a distribution (p50/p90/p99), never a mean — averages hide tail. Track error-latency separately from success-latency.

## Prometheus
- Pull model: scrapes `/metrics` over HTTP at `scrape_interval` (15s typical). Pushgateway only for short-lived batch jobs.
- Service discovery: `kubernetes_sd`, `consul_sd`, file_sd; `relabel_configs` to filter/rewrite targets; `metric_relabel_configs` to drop metrics before ingest.
- PromQL essentials:
```promql
sum(rate(http_requests_total{job="api"}[5m])) by (route)        # req/s per route
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))                          # error ratio
histogram_quantile(0.99, sum(rate(http_req_duration_seconds_bucket[5m])) by (le))
```
- `rate()` = per-second avg over range (counters, handles resets). `irate()` = instant, for fast-moving graphs. `increase()` = total over window. Always give ranges ≥ 4× scrape interval.
- Recording rules precompute expensive queries; alerting rules fire to Alertmanager (dedup, grouping, silences, routing).
- Cardinality: series count = product of label value counts. Never put unbounded values (user_id, request_id, full URL, email) in labels — this is the #1 Prometheus outage cause. Long-term/high-cardinality: Thanos, Cortex, Mimir, VictoriaMetrics.

## Structured logging
- Emit JSON (or logfmt), not free text: `{"ts","level","msg","service","trace_id","span_id","user_id","latency_ms"}`. Machine-parseable, queryable.
- Levels: ERROR (needs action), WARN (recoverable/degraded), INFO (state changes, requests), DEBUG (dev detail, off in prod), TRACE. Set prod default INFO.
- Correlation: inject `trace_id`/`request_id` at ingress, propagate through context, log on every line. Enables stitching logs across services.
- Sampling: for high-volume paths sample INFO (e.g. 1%), but always keep 100% of ERROR/WARN. Tail-based sampling keeps all traces that errored/were slow.
- Cost control: never log in tight loops; no PII/secrets (GDPR + leak risk); ship to Loki/ELK/OpenSearch with retention tiers.

## Distributed tracing + OpenTelemetry
- Span = one unit of work: name, start/end, `trace_id`, `span_id`, `parent_span_id`, attributes, events, status. Trace = tree of spans sharing a trace_id.
- Context propagation: pass trace context across process boundaries via W3C `traceparent` header (`00-<trace_id>-<span_id>-<flags>`). Broken propagation = orphan traces.
- OpenTelemetry (OTel): vendor-neutral standard = API + SDK + Collector + OTLP wire protocol. Auto-instrumentation for common libs; manual spans for business logic. Collector receives/processes/exports (batch, tail-sampling, redaction) to Jaeger, Tempo, Datadog, etc.
- Sampling: head-based (decide at root, cheap, may miss rare errors) vs tail-based (decide after trace completes in Collector, keeps errors/slow — needs buffering). Record baggage for cross-cutting attributes.

## Dashboards (Grafana)
- One row per RED/USE dimension; top-level "is it healthy" view first, drill-down below. Use `$variable` templating for env/service/instance.
- Show rates and ratios, not raw counters. Percentiles as separate series. Overlay deploy annotations to correlate regressions with releases.
- Link panels to logs (Loki) and traces (Tempo) via exemplars/data links. Avoid >20 panels/dashboard (load + cognitive cost).

## Alerting
- Alert on symptoms (user-visible: high error ratio, high p99 latency, SLO burn) not causes (CPU 90%, single pod down) — causes are runbook context, not pages.
- Every page must be actionable, urgent, and novel; else it's a ticket or a dashboard. Multi-window multi-burn-rate SLO alerts (fast 1h + slow 6h window) balance detection speed vs false positives.
- `for:` duration to avoid flapping; group + inhibit in Alertmanager to prevent storms; route by severity/team; enforce silences during maintenance.
- Track alert precision (% actionable). Page fatigue is measurable: pages/on-call-shift, % auto-resolved, % actioned.

## Cardinality control (checklist)
- Bound label values; move high-cardinality identifiers to logs/traces (exemplars), not metric labels.
- Use `metric_relabel_configs` `drop` for noisy series; aggregate away instance labels in recording rules.
- Alert on `prometheus_tsdb_head_series` growth; enforce per-target series limits (`sample_limit`).

## SLI instrumentation
- Instrument SLIs at the point closest to the user (load balancer/gateway) — measure what the user experiences, not internal hops.
- Ratio SLIs: `good_events / valid_events` (e.g. non-5xx / total, requests < 300ms / total). Emit both numerator + denominator as counters so any window works.
- Distinguish availability (did it respond correctly) from latency (fast enough); track independently.
- Emit raw event counters (`good`, `valid`) not pre-computed ratios so downstream can recompute over any window and combine across instances. Percentile SLIs need histograms, not gauges.

## Pull vs push, and collection topology
- Prometheus pull: server discovers + scrapes targets; easy target liveness (`up` metric), no client-side buffering. Firewall/NAT-hostile.
- Push (OTLP, StatsD, Graphite): client emits; needed for serverless/short-lived/edge where targets aren't scrapeable. Requires an aggregation gateway.
- OTel Collector as a fleet-wide funnel: receives OTLP, batches, tail-samples, redacts PII, re-labels, and fans out to multiple backends — decouples app instrumentation from vendor choice. Run as agent (per-node DaemonSet) + gateway (central) tiers.
- Metric naming (Prometheus): `<namespace>_<subsystem>_<unit>` with base units + suffix, e.g. `http_request_duration_seconds`, counters end `_total`. Consistent units make PromQL + dashboards portable.

## Retention + cost tiers
- Metrics cheapest, keep 13+ months (downsampled) for capacity trends; raw high-res 15d, downsample after.
- Traces sampled 1-10% (tail-keep errors/slow at 100%), 7-30d.
- Logs most expensive per byte: hot index days, warm/cold object storage weeks, then delete. Tier by log level + source.

## Gotchas -> Fix
- High-cardinality label (user_id/request_id/URL) explodes TSDB, OOMs Prometheus -> drop via `metric_relabel_configs`; move to trace/log; enforce `sample_limit`.
- Averaging percentiles across instances / using Summary for fleet p99 -> use Histogram + `histogram_quantile` over summed bucket rates.
- Alerting on causes (CPU high, one pod down) -> page on symptoms/SLO burn; keep resource alerts as dashboards/runbook context.
- Alert fatigue, ignored pages -> delete non-actionable alerts; add `for:`; group/inhibit; adopt multi-burn-rate SLO alerts; measure page precision.
- Log spam / logging in loops / PII in logs -> sample INFO (keep 100% ERROR), rate-limit, redact at Collector, tiered retention.
- Missing/orphan traces -> propagate W3C `traceparent`; verify context across async boundaries + message queues; add tail-sampling to keep errors.
- `rate()` on a gauge or raw counter value on dashboard -> `rate()`/`increase()` only on counters; gauges use avg/max.
- Mean latency hides tail -> always graph p50/p90/p99 distributions.
- Metrics say "error rate up" but no way to find which requests -> add exemplars linking histogram buckets to trace IDs; correlate via trace_id in logs.
- Pull scrape misses short-lived batch job metrics -> Pushgateway (and delete after) or OTel push; don't Pushgateway long-running services.
- Dashboards built per-incident, none for steady state -> standardize RED per service + USE per resource + Four Golden Signals.
- Histogram buckets too coarse, p99 unusable -> define buckets around your SLO threshold (dense near the boundary).
