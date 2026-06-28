# Kubernetes Workload Patterns

## Deployment

Use for stateless replicated services. Validate with:

- kubectl get deploy
- kubectl rollout status deploy/<name>
- kubectl describe deploy/<name>
- kubectl get rs
- kubectl get pods -l <selector>

## StatefulSet

Use when stable network identity or persistent volume identity matters.

## DaemonSet

Use for node-level agents such as log collectors, CNI components, or monitoring agents.

## Jobs and CronJobs

Use for finite batch work or scheduled batch work.

## Common Workload Errors

- CrashLoopBackOff: container repeatedly exits or probe kills it.
- ImagePullBackOff: image cannot be pulled due registry, tag, auth, or network issue.
- Pending: scheduler cannot place the Pod or volume cannot bind.
- CreateContainerConfigError: ConfigMap/Secret/env/volume problem.
- OOMKilled: memory limit exceeded.
