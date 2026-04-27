<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: tooling
  tags: [tools, auditors, review, contracts, ci]
  owner: platform
  status: active
-->

# tools/

Long-running automation: auditors, reviewers, contract verifiers, infra helpers, dev hooks. The codified knowledge of "what good looks like" in this repo.

## Purpose

`tools/` is where invariants are turned into checks. Anything that says *"this repo must be true"* — and runs in CI or on a developer's laptop to assert it — lives here.

## What lives here

| Path | Responsibility |
|---|---|
| `tools/auditors/` | Static and dynamic auditors. Detect banned imports, missing L9 headers, contract drift. |
| `tools/review/` | The reviewer pipeline — `analyzers/`, `llm/prompts/`, `policy/`, `schemas/`. Powers the audit agent. |
| `tools/audit_engine.py`, `audit_dispatch.py` | Orchestrates auditor runs and aggregates findings. |
| `tools/verify_contracts.py` | Validates every YAML under `contracts/` against `contracts/_schemas/l9_contract_meta.schema.json`. |
| `tools/dev/` | Developer utilities — local linters, generators, scaffolders. |
| `tools/hooks/` | Pre-commit hook implementations referenced by `.pre-commit-config.yaml`. |
| `tools/deploy/` | Helpers used by deploy scripts (image tagging, manifest mutation). |
| `tools/infra/` | Helpers for environment bring-up that are too logic-heavy for `scripts/`. |
| `tools/l9_template_manifest.yaml` | The authoritative file inventory enforced by template compliance checks. |
| `tools/test.sh` | One-shot script that runs the audit + review + contract verify suite. |

## What does NOT live here

- **No request-path code.** The chassis and engines never import from `tools/`.
- **No production secrets or service config.** Tools are inert outside CI/local dev.
- **No domain logic.** Auditors are policy enforcers, not feature owners.

## Contracts that govern this directory

- [`/contracts/_schemas/l9_contract_meta.schema.json`](../contracts/_schemas/l9_contract_meta.schema.json) — meta-schema that `verify_contracts.py` enforces.
- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — auditors check handlers against this.
- [`/contracts/gate/gate.contract.yaml`](../contracts/gate/gate.contract.yaml) — auditors check the chassis execute path against this.

## Quality gates

- `tools/verify_contracts.py` runs in CI; non-zero blocks merge.
- `tools/auditors/` runs in CI; a single FAIL blocks merge.
- Reviewer prompts under `tools/review/llm/prompts/` are schema-validated against `tools/review/schemas/`.
- Tools themselves are tested under `tests/unit/tools/` and `tests/compliance/`.

## Conventions

- Auditors emit findings as JSON on stdout. Schema in `tools/review/schemas/`.
- Each auditor declares: `id`, `severity` (`block`, `warn`, `info`), `scope` (paths it inspects), `rationale`.
- Reviewer prompts are versioned and immutable once shipped; new prompt → new prompt id.
- New invariants are added by writing an auditor, not by patching the engine.
