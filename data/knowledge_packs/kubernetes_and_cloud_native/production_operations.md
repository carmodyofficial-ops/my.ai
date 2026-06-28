# Kubernetes Production Operations

## Production Concerns

- cluster upgrades
- node lifecycle
- backup and restore
- disaster recovery
- resource requests and limits
- autoscaling
- pod disruption budgets
- ingress and certificate management
- image provenance and vulnerability scanning
- audit logs
- RBAC reviews
- secret rotation
- observability and alerting

## Managed Clusters

EKS, AKS, and GKE reduce some control-plane burden but still require workload, network, IAM/RBAC, and operational discipline.

## Change Safety

Production Kubernetes changes should include:

- dry-run or render step
- diff review
- rollout status check
- rollback command
- blast-radius assessment
