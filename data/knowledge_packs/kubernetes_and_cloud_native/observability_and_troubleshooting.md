# Kubernetes Observability and Troubleshooting

## First Commands

- kubectl get pods -A
- kubectl describe pod <pod> -n <namespace>
- kubectl logs <pod> -n <namespace>
- kubectl logs <pod> -c <container> --previous
- kubectl get events -A --sort-by=.lastTimestamp
- kubectl top pods -A
- kubectl top nodes

## CrashLoopBackOff Checklist

1. Check current and previous logs.
2. Describe the Pod and review events.
3. Check command, args, env, ConfigMaps, Secrets, and mounted volumes.
4. Check liveness/readiness/startup probes.
5. Check resource limits and OOMKilled status.
6. Check image version and recent rollout.
7. Roll back if a recent deployment caused the issue.

## Pending Pod Checklist

- insufficient CPU/memory
- node selector or affinity prevents scheduling
- taints require tolerations
- PVC not bound
- image pull secret not available
- quota or limit range constraints

## DNS Checklist

- CoreDNS pods healthy
- service exists
- endpoints exist
- namespace correct
- network policy not blocking DNS
