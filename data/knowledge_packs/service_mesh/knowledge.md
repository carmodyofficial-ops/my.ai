# Service Mesh

## What & why
- A dedicated infra layer for **service-to-service** communication: a **sidecar proxy** (or per-node proxy) intercepts all pod traffic, adding traffic management, mTLS, retries, and observability **without app code changes** (language-agnostic).
- Splits into **data plane** (proxies, e.g. **Envoy**, that move bytes) and **control plane** (e.g. Istio `istiod`) that configures proxies via xDS APIs (LDS/RDS/CDS/EDS) and distributes certs.
- Solves cross-cutting concerns you'd otherwise reimplement per service/language: uniform TLS, retries/timeouts, circuit breaking, golden metrics, tracing propagation, canary routing.

## Data plane vs control plane
- **Sidecar model**: an Envoy container injected into every pod; iptables (or eBPF/CNI) redirects inbound+outbound through it. Each proxy is a policy enforcement point.
- **Control plane** watches k8s API + mesh CRDs, computes per-proxy config, pushes over gRPC (xDS), issues/rotates workload certs (SPIFFE identities).
- Istio components consolidated into `istiod` (Pilot+Citadel+Galley). Linkerd control plane = `destination`, `identity`, `proxy-injector`.

## mTLS & zero-trust
- Mesh mints a SPIFFE identity per workload (`spiffe://cluster.local/ns/<ns>/sa/<sa>`) tied to the ServiceAccount; proxies do mutual TLS automatically, rotating short-lived certs (Istio default 24h).
- Istio `PeerAuthentication` mode: `PERMISSIVE` (accept plaintext+mTLS — migration default) vs `STRICT` (reject plaintext). `AuthorizationPolicy` = L7 allow/deny by identity/path/method (zero-trust: default-deny, explicit allow).
- Value: encryption + authN identity for east-west traffic with no app changes; authZ on service identity, not IP.

## Traffic management (Istio)
- **`VirtualService`**: routing rules — match host/path/header -> route to subsets with weights; retries, timeouts, fault injection, mirroring live here.
- **`DestinationRule`**: policy for a destination — defines `subsets` (label selectors like `version: v1`), load-balancing (`ROUND_ROBIN`/`LEAST_REQUEST`), connection pool limits, `outlierDetection` (circuit breaking), and `trafficPolicy.tls`.
- **`Gateway`**: L4-L6 ingress/egress at the mesh edge (bound to an ingress-gateway proxy); pair with a `VirtualService` for L7 rules.
```yaml
# 90/10 canary
http:
- route:
  - { destination: { host: svc, subset: v1 }, weight: 90 }
  - { destination: { host: svc, subset: v2 }, weight: 10 }
  retries: { attempts: 3, perTryTimeout: 2s, retryOn: 5xx,reset }
  timeout: 5s
  fault: { delay: { percentage: { value: 10 }, fixedDelay: 5s } }
```
- **Circuit breaking**: `connectionPool` (max conns/pending) + `outlierDetection` (eject hosts after N consecutive 5xx) in `DestinationRule` — sheds load, ejects unhealthy endpoints.
- **Retries/timeouts**: mesh-level, so consistent across languages; budget them (retries multiply load).
- **Fault injection**: inject `delay` or `abort` (HTTP status) at a percentage — test resilience without touching app.
- **Mirroring/shadow**: `mirror` sends a copy of live traffic to a new version (response discarded).

## Observability
- Proxies emit **golden metrics** (request rate, error rate, latency histograms, TCP bytes) with consistent labels -> Prometheus; dashboards (Grafana/Kiali).
- **Distributed tracing**: proxies participate in spans but **the app must forward trace headers** (`x-request-id`, `traceparent`/B3) — the mesh can't stitch spans across a hop otherwise.
- Kiali visualizes the service graph + config validation; access logs per proxy.

## Istio vs Linkerd vs ambient
- **Istio**: Envoy-based, most features/knobs, heavier; broad ecosystem, complex CRD surface.
- **Linkerd**: purpose-built Rust **micro-proxy** (`linkerd2-proxy`), lighter/lower-latency, simpler, opinionated; fewer L7 knobs, no built-in ingress. Great "just want mTLS + metrics + retries."
- **Ambient / sidecarless (Istio ambient)**: drops per-pod sidecars for a per-node **ztunnel** (L4 mTLS/identity) + optional per-namespace **waypoint** proxy for L7 — cuts per-pod overhead and injection restarts; Cilium mesh uses eBPF similarly.

## When it's worth it (vs overkill)
- Worth it: many services in multiple languages; need uniform mTLS/zero-trust; require canary/traffic-shifting, consistent retries/timeouts, and golden-signal observability you can't get per-app.
- Overkill: a handful of services, single language (a shared library/gateway suffices), or a small team without capacity for the operational burden. Consider an API gateway + library-level resilience (or the k8s Gateway API) first.

## Linkerd specifics
- Install `linkerd install | kubectl apply`; inject via `linkerd.io/inject: enabled` namespace annotation or `linkerd inject`. mTLS on by default, automatic, zero-config.
- CRDs: `ServiceProfile` (per-route metrics, retries, timeouts), `HTTPRoute`/`TrafficSplit` (Gateway API-based traffic shifting for canaries via Flagger). `linkerd viz` for dashboards/tap; `linkerd tap deploy/x` live-inspects requests.
- Multicluster via `linkerd multicluster link` + gateway; no separate ingress (bring your own).

## Gateway API & mesh interop
- The k8s **Gateway API** (`GatewayClass`, `Gateway`, `HTTPRoute`, `GRPCRoute`) is the emerging standard replacing bespoke ingress + some mesh CRDs; GAMMA extends it to east-west/mesh routing. Istio and Linkerd both implement it — prefer `HTTPRoute` over vendor CRDs for portability where feature parity exists.
- Retry/timeout/traffic-split now expressible in `HTTPRoute` filters + backendRefs weights.

## Operational visibility
- `istioctl proxy-status` (config sync state across proxies), `istioctl proxy-config {clusters,listeners,routes,endpoints,secret} <pod>` (dump Envoy config), `istioctl analyze -n ns` (config lint), `istioctl dashboard kiali/envoy/grafana`.
- Envoy response flags in access logs decode failures: `UH` no healthy upstream, `UF` upstream conn fail, `UO` overflow (circuit break), `NR` no route, `URX` retry limit, `DC` downstream disconnect. Learn these before debugging 503s.

## Gotchas -> Fix
- **Latency + resource overhead** -> every hop adds a proxy round-trip and each pod gains ~50-100m CPU / tens-of-MB RAM -> budget cluster capacity; use Linkerd or ambient mode for lower overhead; scope the mesh (only meshed namespaces).
- **Sidecar startup race** (app starts before Envoy ready, or app exits but sidecar lingers keeping the pod Running) -> enable native sidecars (k8s 1.29+ `restartPolicy: Always` init container / Istio `ISTIO_NATIVE_SIDECARS`), or `holdApplicationUntilProxyStarts`; handle proxy `/quitquitquit` for Jobs.
- **mTLS STRICT breaks non-mesh clients** -> flipping to STRICT rejects any plaintext (monitoring, k8s probes bypassing proxy, cross-namespace unmeshed) -> migrate via `PERMISSIVE`, verify with metrics, then STRICT; exclude health-check ports.
- **AuthorizationPolicy default-deny locks you out** -> an empty-spec `AuthorizationPolicy` in a namespace denies all -> stage policies, test with `PERMISSIVE`/audit action; remember rules are ALLOW unless a DENY matches.
- **Tracing spans disconnected** -> app doesn't propagate `traceparent`/b3 headers -> instrument apps to forward inbound trace headers; mesh only adds hop spans.
- **Retries amplify outages** (retry storms) -> layered retries (client + mesh + server) multiply load on a struggling service -> set retry budgets, `retryOn` conservatively, pair with circuit breaking/outlier detection.
- **Debugging is harder** -> traffic silently rerouted/dropped by a proxy -> `istioctl proxy-config routes/clusters/endpoints <pod>`, `istioctl analyze`, check Envoy access logs + `503 UC/UF/NR` flags before blaming the app.
- **VirtualService without matching DestinationRule subset -> 503** -> `subset` referenced but not defined -> define subsets + labels in DestinationRule; ensure pods carry the version label.
- **Premature adoption** -> mesh added before there's a real multi-service problem -> the CRD/operational cost dwarfs the benefit; start with an ingress/gateway + libraries, adopt mesh when scale demands.
- **Upgrade blast radius** -> control-plane/proxy version skew or a bad rollout restarts every pod -> use revisioned installs / canary the control plane (`istioctl` revisions), upgrade data plane by re-injecting per-namespace.
- **Egress surprises** -> mesh may block or not observe external calls; strict egress needs `ServiceEntry` / egress gateway -> declare external deps as `ServiceEntry`.
- **eBPF/CNI conflicts** -> mesh iptables redirection clashes with some CNIs/NetworkPolicies -> use the CNI plugin mode, order init containers correctly.
- **Metrics cardinality explosion** -> per-path/per-source labels blow up Prometheus -> aggregate routes (ServiceProfile/`request_operation`), drop high-cardinality labels, sample.
- **mTLS hides identity from L7 policy that expects source IP** -> IP-based NetworkPolicy no longer meaningful with a shared proxy identity -> switch authZ to `AuthorizationPolicy`/`ServiceProfile` on SPIFFE identity, not IP.
- **Headless services / non-HTTP protocols mis-detected** -> Envoy auto-protocol detection guesses wrong (mistakes a binary protocol for HTTP) -> name the service port `tcp-`/`grpc-`/`http-` per Istio convention, or set `appProtocol`.
- **Cross-namespace / multi-cluster routing broken** -> short service name resolves to wrong namespace, or clusters lack a shared trust root -> use FQDNs (`svc.ns.svc.cluster.local`), establish a common root CA / `ServiceEntry` for remote clusters.
- **PILOT push storms at scale** -> thousands of services/proxies overload istiod -> scope proxy config with `Sidecar` resources (limit each proxy's visibility to needed services), enable delta xDS, scale istiod.
