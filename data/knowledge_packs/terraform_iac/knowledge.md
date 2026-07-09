# Terraform / IaC

## Core model
- Declarative HCL describes desired state; Terraform diffs desired vs recorded state vs real infra, then makes API calls to converge.
- Blocks: `provider` (auth + API target), `resource` (managed, created/updated/destroyed by TF), `data` (read-only lookup of existing infra), `variable`/`output`/`locals`, `module`.
- `resource "aws_instance" "web" { ... }` -> address `aws_instance.web`; reference attrs as `aws_instance.web.id`. Data source address `data.aws_ami.ubuntu.id`.
- Workflow: `terraform init` (download providers/modules, configure backend) -> `plan` (preview diff, no changes) -> `apply` (execute) -> `destroy` (tear down). `plan -out=tf.plan` then `apply tf.plan` for exact, reviewed changes.
- Everything is a graph: TF builds a DAG from references and parallelizes independent nodes. Order comes from dependencies, not file position or top-to-bottom.

## State (the critical part)
- State file (`terraform.tfstate`) maps config addresses to real resource IDs + caches attributes. Source of truth for what TF manages. Losing/corrupting it means TF no longer knows it owns resources.
- **State contains secrets in plaintext** (DB passwords, keys, `sensitive` values). Never commit local state to git. Encrypt at rest.
- Remote backend for teams: S3 + DynamoDB lock table, Terraform Cloud, GCS, azurerm. Enables shared state + **locking** so two applies can't corrupt state.
```hcl
terraform {
  backend "s3" {
    bucket         = "tf-state"
    key            = "prod/network.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tf-locks"   # state locking
    encrypt        = true
  }
}
```
- Locking prevents concurrent writes; a crashed apply can leave a stale lock -> `terraform force-unlock <LOCK_ID>` (only after confirming no apply is running).
- State surgery: `terraform state list`, `state show <addr>`, `state mv <old> <new>` (rename without destroy/recreate), `state rm <addr>` (stop managing, don't destroy real resource), `import` (adopt existing infra).
- Never hand-edit state JSON. Use `state` subcommands.

## Variables, outputs, locals
- `variable "region" { type = string; default = "us-east-1" }`. Types: `string`, `number`, `bool`, `list()`, `map()`, `set()`, `object({...})`, `tuple()`. Add `validation {}` blocks and `sensitive = true` (redacts from CLI/plan output, still plaintext in state).
- Precedence (low->high): defaults < env `TF_VAR_region` < `terraform.tfvars`/`*.auto.tfvars` < `-var-file` < `-var` CLI.
- `output "ip" { value = aws_instance.web.public_ip; sensitive = true }` — outputs are how modules expose values and how you read results; child module outputs are the only way a parent reads its internals.
- `locals { name = "${var.env}-app" }` — named expressions, DRY, computed once. Reference `local.name`.

## Modules
- A module = a directory of `.tf` files. Root module + child modules called via `module "vpc" { source = "..."; ... }`.
- Sources: local `./modules/vpc`, registry `terraform-aws-modules/vpc/aws`, git `git::https://...//subdir?ref=v1.2.0`. **Always pin `version`** (registry) or `?ref=` (git) — unpinned modules break reproducibility.
- Compose: pass inputs as arguments, read child outputs as `module.vpc.vpc_id`. Keep modules focused (a VPC, a service), not "one giant module."
- Provider inheritance: child modules inherit default providers; pass explicitly with `providers = { aws = aws.us_east }` for multi-region.

## count vs for_each
- `count = 3` -> instances indexed `aws_x.this[0..2]`. Addressed by **position**.
- `for_each = toset([...])` or a map -> instances keyed by string `aws_x.this["blue"]`. Addressed by **stable key**.
- **Prefer `for_each`** for sets of similar resources. `count`'s positional index churns: removing the middle element shifts every later index, so TF destroys+recreates everything after it. `for_each` keys are stable — remove one, only that one changes.
- Use `count = var.enabled ? 1 : 0` for conditional creation (feature flag a resource).

## Dependencies & lifecycle
- Implicit deps: reference another resource's attribute -> TF orders automatically. Preferred.
- Explicit: `depends_on = [aws_iam_role_policy.p]` when there's a hidden ordering (e.g. IAM must exist before the thing using it, but no attribute is referenced).
- `lifecycle` block:
  - `create_before_destroy = true` — build replacement before deleting old (zero-downtime; required when the resource can't be deleted while in use). Name/tag must not collide.
  - `prevent_destroy = true` — hard-fail any plan that would destroy this (prod DBs, state buckets).
  - `ignore_changes = [tags, ami]` — stop fighting drift on attributes changed out-of-band (autoscaling, external tooling). `ignore_changes = all` ignores everything post-create.
  - `replace_triggered_by = [...]` — force replacement when another resource changes.

## Drift, import, workspaces
- Drift = real infra changed outside TF. `terraform plan` shows it (refresh reconciles state with reality first). `-refresh-only` to just update state.
- Import existing resources: `import { to = aws_instance.web, id = "i-123" }` block (TF 1.5+) + `terraform plan -generate-config-out=gen.tf`, or legacy `terraform import aws_instance.web i-123`. You must still write matching config or the next plan destroys it.
- Workspaces: multiple named states from one config (`terraform workspace new staging`), switch with `select`. Good for ephemeral/identical envs. **Anti-pattern for prod isolation** — one config, shared backend key prefix; a mistake in the wrong workspace is easy. Prefer **separate directories + separate backends/state** per environment for strong isolation.

## CI/CD & secrets
- Pipeline: `fmt -check` -> `validate` -> `init` -> `plan -out` (post plan to PR) -> manual approval -> `apply tf.plan`. Never `apply -auto-approve` prod from an unreviewed plan.
- Auth via short-lived cloud creds (OIDC federation from GitHub Actions/GitLab), not long-lived keys in env.
- Secrets: never hardcode. Pull from a secrets manager via data sources (`data.aws_secretsmanager_secret_version`), or `TF_VAR_` from the CI secret store. Remember they still land in state -> lock down state backend access.
- Pin `required_version` and provider versions:
```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.40" } }
}
```
- Commit `.terraform.lock.hcl` (provider checksums) for reproducible builds across the team.

## Meta-arguments, expressions, refactoring
- `moved { from = aws_x.old, to = aws_x.new }` block records a refactor so TF renames in state instead of destroy+create — safer than manual `state mv`, reviewed in the plan.
- Dynamic blocks generate repeated nested blocks: `dynamic "ingress" { for_each = var.rules; content { from_port = ingress.value.port } }`.
- Expressions: ternary `cond ? a : b`; `for` comprehensions `{ for k, v in var.m : k => upper(v) }`; splat `aws_instance.web[*].id`; `try(expr, fallback)`; string templates `%{ if x }...%{ endif }`.
- Common functions: `merge`, `lookup`, `coalesce`, `concat`, `flatten`, `templatefile`, `jsonencode`, `cidrsubnet`, `toset`, `zipmap`. Use `terraform console` to test expressions interactively.
- `terraform fmt` (canonical formatting), `terraform validate` (syntax/type check, no API calls), `terraform graph` (dependency DAG), `terraform output -json` (machine-readable results for pipelines).
- Provisioners (`remote-exec`, `local-exec`) are a last resort — non-idempotent, run only on create, break the declarative model. Prefer cloud-init/user_data or config-management tools.

## Gotchas -> Fix
- **State conflict / stale lock**: two applies collide or a run crashed. Fix: use remote backend w/ locking; `force-unlock <id>` only after verifying nothing is running.
- **`count` index churn**: deleting a non-last list element recreates everything after it. Fix: switch to `for_each` with stable keys; migrate existing with `state mv 'x[0]' 'x["a"]'`.
- **Unexpected destroy/recreate**: plan shows `-/+`. A "ForceNew" attribute (name, AZ, subnet) changed. Fix: check *why* it forces replacement; use `create_before_destroy`, or `ignore_changes`, or accept downtime deliberately.
- **Provider version drift**: unpinned `version` upgrades on `init` and changes behavior/plan. Fix: pin with `~>`, commit `.terraform.lock.hcl`, upgrade deliberately via `init -upgrade`.
- **Secrets leaked**: state/plan output/logs. Fix: `sensitive = true`, encrypted remote backend, restrict backend IAM, scrub CI logs; rotate anything printed.
- **`data` source read too early**: data resolves during plan and may reference something not yet created in the same apply. Fix: add `depends_on` to the data block, or split applies.
- **Deleted resource in config still lives in cloud**: removing a block plans a destroy — fine. But removing a *module/backend* mid-refactor can orphan resources. Fix: `state rm` to stop managing without destroying; or `moved {}` blocks for refactors.
- **`for_each` over a computed/unknown value**: "Invalid for_each argument... depends on resource attributes that cannot be determined until apply." Fix: key `for_each` off known values (vars/locals), not other resources' computed outputs; or split into two applies.
- **Terraform "wants to destroy" everything after backend change**: reconfigured backend without migrating state. Fix: `init -migrate-state`; never point a config at an empty backend and apply.
- **`prevent_destroy` blocks a legit teardown**: temporarily remove the flag or target around it — don't `-target` your way through prod carelessly.
- **`-target` overuse**: partial applies desync the graph. Fix: use only for surgical recovery, then run a full plan to reconcile.
- **Drift ignored silently**: `ignore_changes` hides real config rot. Fix: scope it to specific attributes, document why; periodically `plan` without it.
