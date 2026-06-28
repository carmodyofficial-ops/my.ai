# Helm, Kustomize, and GitOps

## Helm

Useful for templated application packaging and release lifecycle.

Inspect with:

- helm list -A
- helm status <release> -n <namespace>
- helm get values <release> -n <namespace>
- helm template ...

## Kustomize

Useful for overlay-based customization without templating.

Inspect with:

- kubectl kustomize <path>
- kustomize build <path>

## GitOps

Argo CD and Flux reconcile cluster state from Git.

Key troubleshooting:

- check reconciliation status
- inspect diff between desired and live state
- identify manual drift
- validate secrets handling
- avoid emergency hotfixes that GitOps will revert unless committed
