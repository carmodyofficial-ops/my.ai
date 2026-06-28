# Kubernetes Core Concepts

## Mental Model

Kubernetes is a desired-state orchestration system. Users declare resources through the API server; controllers continuously reconcile actual state toward desired state.

## Core Objects

- Pod: smallest deployable unit.
- Deployment: manages stateless replicated Pods through ReplicaSets.
- StatefulSet: manages ordered identity and stable storage for stateful workloads.
- DaemonSet: ensures Pods run on selected nodes.
- Job/CronJob: finite or scheduled workloads.
- Service: stable virtual endpoint for Pods.
- Ingress: HTTP/HTTPS routing into Services.
- ConfigMap: non-secret configuration.
- Secret: sensitive configuration object, still requiring careful handling.
- Namespace: logical isolation boundary.
- ServiceAccount: workload identity inside the cluster.
- RBAC Role/ClusterRole and RoleBinding/ClusterRoleBinding: permissions model.

## Reconciliation Loop

Troubleshooting should ask:

1. What desired state was declared?
2. What actual state exists?
3. Which controller owns the object?
4. What events were produced?
5. What logs or probes explain failure?
6. What changed recently?
