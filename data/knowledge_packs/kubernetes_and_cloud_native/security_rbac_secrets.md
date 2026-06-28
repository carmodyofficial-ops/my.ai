# Kubernetes Security, RBAC, and Secrets

## RBAC

Kubernetes permissions are controlled by:

- Role / ClusterRole
- RoleBinding / ClusterRoleBinding
- ServiceAccount
- verbs such as get, list, watch, create, update, patch, delete
- resources and API groups

## Safe RBAC Pattern

Prefer least privilege:

- grant namespace-scoped Role when possible
- avoid cluster-admin
- avoid wildcard resources and verbs
- bind only to required service accounts
- validate with kubectl auth can-i

## Secrets

Kubernetes Secret objects are sensitive but not automatically safe. Treat them as guarded operational data.

Safe handling:

- do not print secret values into logs
- avoid committing secrets to Git
- use sealed secrets, external secrets, or cloud secret managers when appropriate
- rotate leaked secrets
- restrict RBAC access to secrets

## Security Debug Commands

- kubectl auth can-i <verb> <resource> --as system:serviceaccount:<ns>:<sa>
- kubectl get role,rolebinding -n <namespace>
- kubectl get clusterrole,clusterrolebinding
- kubectl describe sa <name> -n <namespace>
