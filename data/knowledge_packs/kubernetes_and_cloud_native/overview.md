# Kubernetes and Cloud Native — Overview

## Purpose

This pack gives my.ai operational knowledge for Kubernetes and cloud-native systems.

## Covered Areas

- Kubernetes architecture: control plane, nodes, kubelet, scheduler, controller manager, API server, etcd.
- Core resources: Pods, Deployments, ReplicaSets, StatefulSets, DaemonSets, Jobs, CronJobs.
- Networking: Services, ClusterIP, NodePort, LoadBalancer, Ingress, DNS, CoreDNS, NetworkPolicy.
- Configuration: ConfigMaps, Secrets, environment variables, projected volumes.
- Security: RBAC, service accounts, pod security, secret handling, image security.
- Operations: kubectl, events, logs, describe, rollout status, rollout undo, resource requests/limits.
- Packaging: Helm, Kustomize, GitOps, Argo CD, Flux.
- Storage: PV, PVC, StorageClass, StatefulSet storage behavior.
- Observability: metrics, logs, events, probes, tracing, Prometheus/Grafana patterns.
- Local clusters: kind, minikube, k3s.
- Production clusters: EKS, AKS, GKE, bare metal, hybrid clusters.

## Response Standard

For Kubernetes questions, my.ai should provide:

- direct diagnosis or explanation
- likely causes
- safe kubectl inspection commands
- risks and assumptions
- validation steps
- rollback or remediation path when appropriate
