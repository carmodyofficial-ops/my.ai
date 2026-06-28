# Kubernetes & Cloud-Native Reference

## Objects — when to use
- **Pod**: never directly; managed by controllers.
- **Deployment**: stateless apps (replicas, rolling updates).
- **StatefulSet**: stable IDs + per-pod PVC (DBs, Kafka).
- **DaemonSet**: one pod/node (logging, CNI).
- **Job/CronJob**: run-to-completion / scheduled.
- **Service**: `ClusterIP` (internal), `NodePort` (node:port), `LoadBalancer` (cloud LB). **Ingress**: HTTP routing + TLS.
- **ConfigMap** non-secret config; **Secret** credentials; **PVC** persistent storage.

## Minimal Deployment + Service
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 3
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
      - name: web
        image: myapp:1.4.2   # never :latest
        ports: [{containerPort: 8080}]
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        readinessProbe: {httpGet: {path: /ready, port: 8080}}
        livenessProbe:  {httpGet: {path: /health, port: 8080}}
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}   # must match pod labels
  ports: [{port: 80, targetPort: 8080}]
```

## Key concepts
- **Selectors**: Service routes to Pods whose labels match `spec.selector`. Mismatch = 0 endpoints.
- **requests** = scheduling/guarantee; **limits** = cap. Exceed mem limit → **OOMKilled**.
- **readiness** gates traffic; **liveness** restarts a hung container. Don't make liveness too aggressive.
- **Namespaces**: isolate/quota; `-n prod`.

## Rollout
`kubectl rollout status/history/undo deploy/web` — `undo` reverts last revision.

## Debug flow
`get pods` → `describe pod X` (events/probes) → `logs X [-p]` → `exec -it X -- sh` → `get events --sort-by=.lastTimestamp`.

## Mistakes → fix
- No limits → noisy neighbor/OOM → set requests+limits.
- Missing readiness → traffic to cold pods → add probe.
- `:latest` → no rollback → pin digest/tag.
- Secret in ConfigMap/git → use Secret + sealed-secrets.
- **CrashLoopBackOff** → `logs -p` (app error).
- **ImagePullBackOff** → bad tag/registry auth → check `describe`, imagePullSecrets.
- No endpoints → label/selector mismatch → `get endpoints web`.
