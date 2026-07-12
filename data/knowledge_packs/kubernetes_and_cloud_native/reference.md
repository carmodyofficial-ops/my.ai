# Kubernetes & Cloud-Native Reference

## Objects — when to use
- **Pod**: smallest unit (1+ containers sharing net/IPC/volumes); never create directly — use a controller.
- **ReplicaSet**: keeps N pod replicas; you rarely touch it — owned by a Deployment.
- **Deployment**: stateless apps; manages ReplicaSets for rolling updates + rollback.
- **StatefulSet**: stable network IDs (`web-0`,`web-1`) + stable per-pod PVC + ordered rollout (DBs, Kafka, Zookeeper).
- **DaemonSet**: exactly one pod per (matching) node — log shippers, node exporters, CNI agents.
- **Job**: run-to-completion (`completions`/`parallelism`, `backoffLimit`). **CronJob**: scheduled Jobs (UTC cron).
- **Service**: stable virtual IP + DNS in front of pods. **Ingress**: L7 HTTP(S) routing + TLS termination (needs an ingress controller).
- **ConfigMap**: non-secret config (files/env). **Secret**: base64 (NOT encrypted at rest by default — enable etcd encryption) credentials.
- **PVC/PV/StorageClass**: request/back/provision durable storage.

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
        image: myapp:1.4.2            # never :latest
        ports: [{containerPort: 8080}]
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits:   {cpu: 500m, memory: 256Mi}
        readinessProbe: {httpGet: {path: /ready,  port: 8080}}
        livenessProbe:  {httpGet: {path: /health, port: 8080}, initialDelaySeconds: 15}
        startupProbe:   {httpGet: {path: /health, port: 8080}, failureThreshold: 30, periodSeconds: 5}
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}                # MUST match pod labels
  ports: [{port: 80, targetPort: 8080}]
```

## Scheduling — requests/limits, affinity, taints
- **requests** = what the scheduler reserves + guarantees (basis for bin-packing). **limits** = hard cap. No request -> scheduler assumes ~0, overcommits the node.
- CPU limit -> **throttled** (CFS) when exceeded (not killed). Memory limit exceeded -> **OOMKilled** (137).
- QoS: `Guaranteed` (requests==limits all containers), `Burstable`, `BestEffort` (no requests) — BestEffort evicted first under node pressure.
- **nodeSelector** / **nodeAffinity** (required/preferred) pin pods to nodes by label. **podAffinity/antiAffinity** co-locate or spread (e.g. spread replicas across zones with `topologySpreadConstraints`).
- **Taints** repel pods from nodes (`kubectl taint node n key=v:NoSchedule`); pods need a matching **toleration** to land there (dedicated/GPU nodes, control plane).

## Health probes
- **readiness**: gates Service endpoints — fail = pulled from load balancing, pod NOT restarted. Use for "not ready for traffic" (warming, dependency down).
- **liveness**: fail past `failureThreshold` = **kubelet restarts the container**. Keep it cheap + independent of downstreams (or a slow dependency triggers restart storms). Too aggressive -> crash loops.
- **startupProbe**: disables liveness/readiness until it passes — for slow-booting apps so liveness doesn't kill them mid-boot.
- Types: `httpGet`, `tcpSocket`, `exec`, `grpc`.

## Rolling updates + rollback
- Deployment default `RollingUpdate` (`maxSurge`/`maxUnavailable`); `Recreate` kills all then recreates.
- `kubectl rollout status/history/undo deploy/web` — `undo` reverts to previous ReplicaSet (kept per `revisionHistoryLimit`). A new rollout triggers only on **pod template** change (bump the image; changing only a ConfigMap does NOT roll — checksum-annotate the template).
- `kubectl rollout restart deploy/web` forces a fresh roll.

## Autoscaling
- **HPA**: scales replicas on metrics (`kubectl autoscale deploy/web --min 2 --max 10 --cpu-percent 70`); CPU/memory needs metrics-server; custom/external metrics via adapter. **Requests must be set** or CPU% is undefined.
- **VPA** right-sizes requests/limits (don't run alongside HPA on the same CPU metric). **Cluster Autoscaler** adds/removes nodes when pods are unschedulable/idle.

## Namespaces + RBAC
- Namespaces isolate names + apply `ResourceQuota`/`LimitRange`; `-n prod`. Not a security boundary by themselves.
- RBAC: **Role**/**ClusterRole** (verbs on resources) bound via **RoleBinding**/**ClusterRoleBinding** to a user/group/**ServiceAccount**. Pods authenticate as their ServiceAccount. Grant least privilege; avoid `cluster-admin`.

## Storage
- **PVC** (claim: size + access mode + StorageClass) binds to a **PV** (actual volume). **StorageClass** dynamically provisions PVs (cloud disk, CSI driver).
- Access modes: `ReadWriteOnce` (one node — block/EBS), `ReadWriteMany` (many nodes — NFS/EFS), `ReadOnlyMany`. `reclaimPolicy: Retain|Delete`.
- StatefulSet `volumeClaimTemplates` gives each pod its own PVC that survives reschedule.

## Networking
- **CNI** plugin (Calico/Cilium/Flannel) gives every pod a routable IP; flat network, all pods reach all pods unless a **NetworkPolicy** restricts (default is allow-all — policies are deny-by-default *once any policy selects a pod*).
- **Service DNS**: `svc.namespace.svc.cluster.local` (CoreDNS). ClusterIP is a stable VIP load-balanced by kube-proxy (iptables/IPVS) to ready endpoints.
- Service types: `ClusterIP` (internal), `NodePort` (`node:30000-32767`), `LoadBalancer` (cloud LB), `ExternalName` (CNAME). **Headless** (`clusterIP: None`) returns pod IPs directly (StatefulSets, client-side LB).

## Helm / operators
- **Helm**: templated packages ("charts", `values.yaml`), releases, `helm upgrade --install`, rollback, versioning. Kustomize = template-free overlay alternative (`kubectl apply -k`).
- **Operator**: a controller + **CRD** encoding operational knowledge (backup/failover/scaling) for stateful software; reconciles desired -> actual state in a loop.

## Debug flow
`kubectl get pods` -> `describe pod X` (Events, probe failures, scheduling) -> `logs X [-p]` (`-p` = previous crashed container) -> `exec -it X -- sh` -> `get events --sort-by=.lastTimestamp` -> `get endpoints svc` (empty = selector mismatch).

## Mistakes -> Fix
- **No resource limits**: noisy neighbor / node OOM / eviction -> set requests+limits; enforce with LimitRange.
- **OOMKilled (137)**: memory limit too low / leak -> raise limit or fix; check `describe` -> Last State.
- **CrashLoopBackOff**: app exits/panics -> `logs -p`, fix config/env; check exit code.
- **ImagePullBackOff / ErrImagePull**: bad tag, private registry, no auth -> `describe` events; add `imagePullSecrets`; verify tag/digest.
- **Liveness too aggressive**: restarts under load / slow deps -> loosen thresholds, use startupProbe, decouple from downstreams.
- **Missing readiness**: traffic to cold/broken pods (503s during rollout) -> add readinessProbe.
- **Pending pod**: insufficient CPU/mem, no matching node (taint/affinity), unbound PVC -> `describe` -> Events; scale nodes or fix constraints.
- **Service returns nothing / no endpoints**: `selector` != pod labels, or pods not Ready -> `get endpoints`, fix labels/probes.
- **Secrets in env/ConfigMap/git**: visible, logged, committed -> Secret objects + etcd encryption + external secrets (Vault/sealed-secrets); mount as files over env where possible.
- **hostPort/hostNetwork**: port conflicts, only-one-per-node, breaks scheduling -> use a Service/Ingress instead.
- **DNS failures / slow lookups**: CoreDNS down, `ndots:5` search-domain overhead -> check CoreDNS pods, use FQDN with trailing dot for external hosts.
- **`:latest` image**: no rollback, cache surprises, nodes disagree -> pin tag/digest, `imagePullPolicy: IfNotPresent`.
- **ConfigMap change didn't redeploy**: pods don't auto-restart -> checksum annotation on pod template or `rollout restart`.
