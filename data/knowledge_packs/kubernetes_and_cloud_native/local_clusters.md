# Local Kubernetes Clusters

## kind

Good for CI, local testing, and disposable clusters.

## minikube

Good for local developer clusters with addon support.

## k3s

Good for lightweight homelab, edge, and LAN-hosted services.

## my.ai Local Cluster Considerations

If my.ai is ever moved to Kubernetes, evaluate:

- persistent storage for memory, Chroma, and application state
- ingress and authentication boundary
- LAN-only exposure
- GPU/device access if local models are involved
- backup/restore strategy
- logs and health probes
- upgrade/rollback process
