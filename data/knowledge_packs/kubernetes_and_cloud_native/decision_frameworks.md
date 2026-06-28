# Kubernetes Decision Frameworks

## Deployment vs StatefulSet vs DaemonSet

- Use Deployment for stateless replicated apps.
- Use StatefulSet for stable identity or storage.
- Use DaemonSet for node-local agents.

## Service vs Ingress

- Use Service for stable in-cluster access.
- Use Ingress for HTTP/HTTPS routing into services.
- Use LoadBalancer or MetalLB when external IP allocation is required.

## Helm vs Kustomize

- Helm: packaging, templating, release lifecycle.
- Kustomize: overlays and declarative patching.
- GitOps can use either.

## Local vs Managed Cluster

- Local/k3s: control, low cost, homelab/LAN.
- Managed/EKS/AKS/GKE: operational maturity, cloud integrations, higher cost/complexity.
