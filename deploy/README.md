<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: deploy
  tags: [deploy, terraform, scripts, release]
  owner: platform
  status: active
-->

# deploy/

Release plumbing. Terraform modules and deploy scripts that turn a built artifact into a running node.

## Purpose

Move a versioned image into an environment with explicit, reviewable, idempotent steps. No ad-hoc `kubectl apply`, no untracked Terraform.

## What lives here

| Path | Responsibility |
|---|---|
| `deploy/scripts/` | Imperative deploy scripts — image promotion, smoke tests, rollback. |
| `deploy/terraform/` | Declarative environment definition — networking, IAM, cluster bindings, secrets references. |

## What does NOT live here

- **No application code.** This directory ships infra, not features.
- **No image builds.** Image build lives in root `Dockerfile.prod` and CI.
- **No production secrets.** Secrets are referenced; never embedded. See `docs/security/SECRETS.md`.
- **No environment-specific Python.** If you need logic, write it in `tools/deploy/` and call it from a script here.

## Contracts that govern this directory

- [`/contracts/registration/node_registration.contract.yaml`](../contracts/registration/node_registration.contract.yaml) — deploy steps must register the node with the routing authority before traffic is admitted.
- [`/contracts/observability/metrics.contract.yaml`](../contracts/observability/metrics.contract.yaml) — readiness gates assert SLI exposure before promotion.

## Deploy invariants

1. **Plan before apply.** Every Terraform change ships a captured plan in the PR.
2. **Health gates.** Promotion waits on `/health/ready` and a minimum SLI window per `docs/runbooks/DEPLOY.md`.
3. **Rollback is a first-class step.** Every script ships a rollback path; CI fails if missing.
4. **No drift.** Terraform state is the source of truth; manual changes are reverted.

## Quality gates

- `terraform fmt -check` and `terraform validate` run in CI.
- `tflint`, `checkov`, and `tfsec` block on findings of `error` or higher.
- Deploy scripts: `set -euo pipefail`, `shellcheck` clean, idempotent.
- `scripts/predeploy_check.py` runs before any apply.

## Conventions

- One module per concern under `deploy/terraform/` — no god-modules.
- Variables typed and documented. No untyped strings.
- Outputs minimal. Expose only what downstream modules need.
- Naming: `<env>-<service>-<concern>` — e.g. `prod-golden-repo-cluster`.
