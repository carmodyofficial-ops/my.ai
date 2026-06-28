# Kubernetes Safety Boundaries

## Destructive Operations

Before recommending destructive actions, verify backups and impact.

High-risk examples:

- deleting PVCs/PVs
- force deleting namespaces
- deleting CRDs
- changing CNI
- rotating cluster certificates
- editing production RBAC
- exposing services publicly
- disabling admission/security controls

## Secrets and Credentials

Never print or store Kubernetes secret values. For troubleshooting, inspect metadata and references without exposing secret data.

## Security Topics

For RBAC, network policy, ingress exposure, TLS, and secret handling, also route to networking_and_security when relevant.

## Production Advice

For production clusters, include validation and rollback steps.
