<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: ci
  tags: [github, ci, workflows, codeowners]
  owner: platform
  status: active
-->

# .github/

GitHub-native automation: workflows, code owners, dependency policy, release drafting.

## Purpose

The CI surface is where invariants are *enforced*. Auditors, contract checks, tests, and policy scans all run from here. If a check exists in `tools/` but is not wired in `.github/workflows/`, it is decoration.

## What lives here

| Path | Responsibility |
|---|---|
| `workflows/` | GitHub Actions workflows — CI, contract verification, audit, release. |
| `CODEOWNERS` | Path-scoped review owners. Required reviewers per directory. |
| `dependabot.yml` | Dependency update cadence and grouping. |
| `release-drafter.yml` | Auto-draft release notes from PR labels. |

## Required workflows

Every workflow ships in CI. Do not remove without an ADR.

- **lint-and-type** — ruff, mypy strict, shellcheck, hadolint.
- **contracts** — `tools/verify_contracts.py` against `contracts/_schemas/l9_contract_meta.schema.json`; `scripts/validate_contract_alignment.py`.
- **audit** — `tools/auditors/` and `tools/audit_engine.py` — fails CI on any `block`-severity finding.
- **tests** — `pytest` over `tests/unit`, `tests/contracts`, `tests/integration`, `tests/compliance`.
- **policy** — semgrep against `.semgrep/`, OPA bundles via `scripts/validate-policy.sh`.
- **build** — Docker image build for `Dockerfile` and `Dockerfile.prod`, hadolint clean.
- **review** — reviewer pipeline (`tools/review/`) on changed files.

## What does NOT live here

- **No application code.** Only CI, ownership, and dependency configuration.
- **No production secrets.** Use repository secrets and OIDC federation; never embed.

## Contracts that govern this directory

- [`/contracts/_schemas/l9_contract_meta.schema.json`](../contracts/_schemas/l9_contract_meta.schema.json) — the contracts workflow validates every YAML against this meta-schema.
- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — the audit workflow asserts handler/contract alignment.

## Quality gates

- Every workflow pins action versions to a SHA, never a moving tag.
- Required status checks: `lint-and-type`, `contracts`, `audit`, `tests`, `policy`.
- `CODEOWNERS` covers `contracts/`, `chassis/`, `engine/`, `tools/auditors/`, `docs/adr/` at minimum.
- Branch protection requires linear history and signed commits on `main`.

## Conventions

- Workflow names: `lower-case-hyphenated`.
- One workflow file per concern. No "ci.yml" mega-workflow.
- Use reusable workflows for common matrices (`workflow_call`).
- All workflow steps run with `set -euo pipefail` semantics where applicable.
