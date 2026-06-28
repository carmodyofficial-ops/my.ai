# Kubernetes Architecture Map

## Control Plane

- API server: front door for all cluster changes.
- etcd: persistent cluster state.
- scheduler: assigns Pods to nodes.
- controller manager: runs reconciliation controllers.
- cloud controller manager: integrates cloud provider resources where applicable.

## Worker Node

- kubelet: node agent that starts and monitors Pods.
- container runtime: containerd or equivalent.
- kube-proxy or CNI dataplane: service/network routing depending on implementation.
- CNI plugin: pod networking, network policy, overlay/underlay behavior.

## Common Failure Areas

- API authentication/authorization failure.
- Bad image or image pull secret.
- Failed scheduling due to resources, taints, affinities, or PVCs.
- Probe failures causing restarts.
- DNS or Service selector mismatch.
- Ingress controller or TLS misconfiguration.
- RBAC denies expected access.
