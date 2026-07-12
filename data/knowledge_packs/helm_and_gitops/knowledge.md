# Helm & GitOps

## Helm core model
- Helm packages Kubernetes manifests into a **chart** (templated YAML) + **values** (config) -> rendered manifests -> applied as a **release** (named install into a namespace). Helm 3 is client-only, no Tiller; release state stored in-cluster as Secrets (`sh.helm.release.v1.<name>.v<rev>`, gzipped base64).
- Chart layout: `Chart.yaml` (metadata: `name`, `version` chart ver, `appVersion` app ver, `dependencies`), `values.yaml` (defaults), `templates/` (Go templates), `templates/_helpers.tpl` (named templates), `charts/` (vendored subcharts), `crds/` (installed before templates, never templated/upgraded).
- Commands: `helm install <rel> <chart> -n ns --create-namespace`, `helm upgrade --install <rel> <chart> -f prod.yaml --set image.tag=1.2`, `helm template` (render locally, no cluster), `helm diff upgrade` (plugin, preview), `helm rollback <rel> <rev>`, `helm history <rel>`, `helm uninstall <rel> --keep-history`.
- `helm upgrade --install` (aka upsert) is the idempotent workhorse; `--atomic` rolls back on failure; `--wait` blocks until resources Ready; `--timeout 5m`; `--dry-run=server` renders + validates against API + admission.

## Templating
- Actions in `{{ }}`; `.Values`, `.Release` (`.Name`,`.Namespace`,`.Revision`,`.IsUpgrade`), `.Chart`, `.Capabilities` (`.APIVersions.Has "batch/v1"`), `.Files`.
- Whitespace: `{{-` trims preceding whitespace incl newline, `-}}` trims following. `{{- if .x }}` on its own line avoids blank lines.
- `nindent N` = newline + indent N spaces (use for embedded blocks); `indent N` no leading newline. `toYaml .Values.resources | nindent 12` is the canonical pattern for injecting a map at correct indent.
- Quote strings: `{{ .Values.tag | quote }}` — numeric-looking or `yes/no/on/off` values otherwise mis-type (YAML 1.1 booleans). Always quote annotation/label values.
- `_helpers.tpl`: `{{- define "app.fullname" -}}...{{- end -}}`, use `{{ include "app.fullname" . }}` (NOT `template` — `include` is a function so its output can pipe to `nindent`).
- `default`, `required "msg" .Values.x` (fail render if unset), `tpl` (render a string as template), `lookup` (read live cluster objects during render — empty on `helm template`/dry-run).
- Scope: `with` and `range` rebind `.`; reach parent via `$` (`$.Release.Name` inside a range).

## Hooks, deps, repos
- Hooks via annotation `"helm.sh/hook": pre-install,pre-upgrade`; `hook-weight` orders; `hook-delete-policy: before-hook-creation,hook-succeeded`. Hook resources are NOT tracked in the release -> not deleted on uninstall unless policy set. Use for migrations, not general ordering.
- Dependencies in `Chart.yaml` -> `helm dependency update` populates `charts/` + `Chart.lock`. Subchart values namespaced under the subchart name (`postgresql:` block); parent overrides child via that key; `global:` values visible to all subcharts. `condition: postgresql.enabled` / `tags:` toggle subcharts.
- Repos: `helm repo add`, `repo update`, `search repo`. **OCI registries** (preferred, no index.yaml): `helm push chart-1.0.tgz oci://ghcr.io/org/charts`, `helm install rel oci://ghcr.io/org/charts/app --version 1.0`.

## GitOps principles
- Four tenets: (1) **declarative** desired state, (2) **git = single source of truth**, versioned + immutable, (3) **pulled automatically** by an in-cluster agent, (4) **continuously reconciled** — agent drives cluster toward git, correcting drift. Contrast push CI/CD (`kubectl apply` from a runner with cluster creds).
- Benefits: audit trail = git history, rollback = `git revert`, PR-based review/approval, no cluster creds in CI, self-healing.

## Argo CD
- `Application` CR = source (repo/path/targetRevision, Helm/Kustomize/plain) + destination (cluster/namespace) + `syncPolicy`.
```yaml
syncPolicy:
  automated: { prune: true, selfHeal: true }
  syncOptions: [CreateNamespace=true, ServerSideApply=true]
```
- `selfHeal` reverts manual `kubectl` drift; `prune` deletes objects removed from git (off by default — orphans linger). Manual sync if no `automated`.
- **Sync waves**: annotation `argocd.argoproj.io/sync-wave: "-1"` orders apply (low first); resource hooks `argocd.argoproj.io/hook: PreSync|Sync|PostSync|SyncFail`.
- Health: built-in for Deployments/etc.; custom Lua health checks for CRDs. Status `Synced/OutOfSync` (git vs live) is separate from `Healthy/Degraded` (runtime).
- **App-of-apps**: a parent Application whose git path contains child Application manifests -> bootstrap many apps. ApplicationSet generators (list/git/cluster/matrix) template Apps across many clusters/envs.

## Flux CD
- Controllers: source-controller (`GitRepository`,`HelmRepository`,`OCIRepository`), kustomize-controller (`Kustomization`), helm-controller (`HelmRelease`), image-automation (write new tags back to git), notification-controller.
- `Kustomization.spec.interval` reconcile cadence; `prune: true`; `dependsOn` orders; `HelmRelease` wraps a chart with `values`. `flux bootstrap github ...` commits Flux's own manifests -> Flux manages itself.

## Secrets in GitOps
- Never commit plaintext secrets. Options:
  - **Sealed Secrets** (Bitnami): `kubeseal` encrypts to a `SealedSecret` (asymmetric, cluster-specific key) -> safe in git; controller decrypts to a `Secret`. Re-seal per cluster; losing the controller key = unrecoverable.
  - **SOPS** (+ age/KMS): encrypt values in-file, keys stay encrypted; Flux decrypts natively (`decryption.provider: sops`), Argo via ksops/plugin.
  - **External Secrets Operator**: `ExternalSecret` pulls from Vault/AWS SM/GCP SM into a `Secret`; only a reference lives in git — best for rotation.

## Progressive delivery
- Argo Rollouts / Flagger drive canary/blue-green via a `Rollout`/`Canary` CR + metric analysis (Prometheus) with automatic rollback on SLO breach; integrates with a service mesh or ingress for traffic weighting.
- Argo Rollouts `Rollout` replaces `Deployment`: `strategy.canary.steps` (`setWeight`, `pause`, `analysis`); `strategy.blueGreen` (`activeService`/`previewService`, `autoPromotionEnabled: false` for manual gate). `AnalysisTemplate` queries metrics; failed run -> auto-abort + full-weight rollback.

## Testing, linting, validation
- `helm lint <chart>` (structure + template errors), `helm template --debug` (see rendered + errors), `helm install --dry-run=server` (API + admission validation).
- `values.schema.json` (JSON Schema) validates `values.yaml` on install/upgrade/template/lint — fail fast on bad/missing config, typed inputs.
- `helm test <rel>` runs pods annotated `"helm.sh/hook": test` (smoke checks post-deploy). `ct` (chart-testing) + `unittest` plugin for CI. `kubeconform`/`kubeval` validate rendered manifests against k8s API schemas.
- `helm get manifest/values/notes/hooks <rel>` inspects a live release; `helm status`; `helm get metadata`.

## Helm vs Kustomize (in GitOps)
- Helm = templating + packaging + release lifecycle + repos; Kustomize = overlay/patch (no templating, no logic), base + env overlays via `kustomization.yaml`. Argo CD and Flux natively support both; combine with Helm-rendered-then-Kustomize-patched (`kustomize build --enable-helm`). Choose Helm for distributable parameterized apps, Kustomize for your own env variants without template complexity.

## Gotchas -> Fix
- **`nindent`/indent wrong -> broken YAML** -> render with `helm template . | kubectl apply --dry-run=client -f -`; use `toYaml x | nindent N` where N matches parent key depth + 2.
- **Unquoted numeric/bool value coerced** (`tag: 1.10` -> `1.1`, `"on"` -> `true`) -> pipe through `| quote`.
- **Values precedence surprise** -> low->high: chart `values.yaml` < parent overrides of subchart < `-f file` (later files win) < `--set` < `--set-string`/`--set-file`. `--set a.b=1` deep-merges; a `-f` file with a *list* fully replaces (no merge). Verify with `helm get values <rel>` and `helm get manifest <rel>`.
- **Argo CD perpetual OutOfSync / sync loop** -> a controller/webhook mutates the object (default fields, `kubectl.kubernetes.io/last-applied`) -> add `ignoreDifferences` (jsonPointers) or `Replace=false`; enable `ServerSideApply=true` to stop last-applied churn.
- **Helm-installed release then Argo/Flux adopts it -> ownership conflict** -> either fully migrate (uninstall keeping resources) or let one tool own; don't `helm upgrade` an Argo-managed app.
- **CRDs not updated** -> Helm installs `crds/` once, never upgrades/deletes them -> manage CRD lifecycle separately (`kubectl apply` CRDs, or put in a templated chart with care).
- **Failed upgrade leaves release `pending-upgrade`** -> `helm rollback <rel>` to last good rev, or `helm upgrade --atomic --cleanup-on-fail`; a stuck pending state after a killed process may need rollback to a prior revision.
- **`helm uninstall` leaves hook resources / PVCs** -> set `hook-delete-policy`; StatefulSet PVCs are never auto-deleted.
- **`helm rollback` doesn't restore data / external state** -> rollback only re-applies stored manifests of a prior revision; DB migrations, deleted PVCs, external resources are NOT reverted.
- **`lookup` returns empty in CI** -> it needs a live cluster; guard template logic so `helm template`/`--dry-run=client` still renders.
- **selfHeal fights an HPA** -> HPA changes `replicas` -> Argo sees drift -> add `ignoreDifferences` on `/spec/replicas` for HPA-managed Deployments.
- **Secret rotated in git but pod keeps old value** -> Secret change doesn't restart pods -> checksum annotation `checksum/config: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}` to force rollout.
- **`appVersion` vs chart `version` confusion** -> bump chart `version` on ANY template change (Argo/Flux/OCI dedupe by chart version); `appVersion` is just the default image tag label.
- **`--reuse-values` drops new defaults** -> `helm upgrade --reuse-values` reuses old values and ignores new chart defaults for keys you didn't `--set` -> prefer `--reset-then-reuse-values`, or always pass the full `-f values.yaml`.
- **Big chart -> Argo CD OOM / timeout** -> huge rendered manifests exceed the `manifest-generate` limits -> raise `--kubectl-parallelism-limit`/repo-server resources, split into ApplicationSets, or enable server-side apply.
- **Namespace-scoped drift not pruned** -> resources removed from git linger because `prune: false` -> enable `prune` cautiously (test in staging; a bad label selector can delete everything) with `PruneLast=true`.
- **`crd-install` / ordering across apps** -> app B needs app A's CRDs first -> use sync waves (Argo) or `dependsOn` (Flux) to order; put CRDs in an earlier wave/app.
