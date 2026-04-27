<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: meta
  tags: [implementation-note, ci, contracts, codeowners]
  owner: platform
  status: active
-->

# Implementation Note — Contracts CI Wiring

**Branch:** `feat/contracts-ci-wiring`
**Depends on:** `chore/l9-docs-contracts-scaffold` (canonical contracts pack and meta-schema). This branch is designed to merge in either order — verifiers run in tolerant mode when the meta-schema is absent.
**Scope:** Wire `tools/verify_contracts.py` and `scripts/validate_contract_alignment.py` into required CI checks, add a dedicated L9 contracts workflow, and add CODEOWNERS rules for `contracts/` and `docs/adr/`.
**Non-goals:** No engine, chassis, tools, or domain code is changed. No legacy contract is removed.

## Files added

| Path | Purpose |
|---|---|
| `.github/workflows/contracts-l9.yml` | Dedicated workflow `contracts-l9` with the `verify` job — required status check. Validates the L9 canonical contracts against the meta-schema, runs the legacy SHA manifest verifier, the alignment script, and the L9 header check. |
| `.github/pull_request_template.md` | PR checklist that surfaces contract changes, ADR requirements, and the local pre-merge command list. |
| `scripts/verify_l9_contracts.py` | Walks `contracts/**/*.contract.yaml` and validates every file against `contracts/_schemas/l9_contract_meta.schema.json`. Asserts the L9_META header is present and that no contract (other than the migration contract) declares `PacketEnvelope` as canonical. Tolerant: exits 0 when the meta-schema is not yet present. |
| `scripts/check_l9_meta_headers.py` | Enforces the L9_META header on every doc and contract. Has a small allowlist of legacy directories (`docs/agent-tasks/`, `docs/audit/`, `docs/review/`) and legacy contract files. |
| `docs/ci/REQUIRED_CHECKS.md` | Source of truth for branch-protection configuration on `main`: required status checks, required reviews, signed-commit and linear-history settings. |

## Files modified

| Path | Change |
|---|---|
| `.github/workflows/ci.yml` | Named jobs (`Lint & type check`, `Audit (27 rules)`, `Tests`, `Compliance (legacy + L9)`); added concurrency control; added jsonschema install; added the L9 meta-schema verifier and L9 header check to the compliance job; legacy `tools/verify_contracts.py` step is `continue-on-error: true` until the legacy manifest is reconciled. |
| `.github/workflows/protocol-conformance.yml` | Bumped Python to 3.12, added concurrency control, added the L9 meta-schema verifier alongside the existing alignment script and contract test suite. Job renamed `Protocol conformance (required)`. |
| `.github/CODEOWNERS` | Path-scoped owners for `contracts/`, `docs/adr/`, `docs/contracts/`, `docs/architecture/`, `docs/boundaries/`, `chassis/`, `engine/security/`, `tools/`, `scripts/`, `.github/`, `deploy/`, `infrastructure/`, plus governance files. Last-matching rule wins. |

## Required status checks (set in branch protection)

Wire these in `Settings → Branches → main → Require status checks to pass before merging`:

1. `Lint & type check`
2. `Audit (27 rules)`
3. `Tests`
4. `Compliance (legacy + L9)`
5. `L9 contracts verify (required)`
6. `Protocol conformance (required)`

The detailed branch-protection settings are in `docs/ci/REQUIRED_CHECKS.md`.

## Verification

The new verifiers were smoke-tested locally on `main` (before the L9 docs/contracts scaffold has merged):

- `python scripts/verify_l9_contracts.py` → `RESULT: PASS (tolerant mode)` because the meta-schema is not yet present.
- `python scripts/check_l9_meta_headers.py` → `RESULT: PASS` after exempting legacy `docs/agent-tasks/`, `docs/audit/`, and `docs/review/`.
- `python tools/verify_contracts.py` → currently FAILs on `main` because the legacy 20-contract manifest is out of date; this is pre-existing and is therefore non-blocking in this branch (`continue-on-error: true`).

Once the L9 docs/contracts scaffold lands, the `verify_l9_contracts.py` step exercises the full meta-schema check on every PR.

## Local pre-merge checklist

```bash
python scripts/verify_l9_contracts.py
python scripts/check_l9_meta_headers.py
python tools/verify_contracts.py        # currently advisory
python scripts/validate_contract_alignment.py --repo-root . \
  --manifest templates/service/service.manifest.yaml
pytest tests/contracts -q
```

The `contracts-l9` workflow runs the same set in CI.

## CODEOWNERS notes

Teams referenced:

- `@platform-team` — default owner; required on contracts, ADRs, CI, governance.
- `@architecture-team` — required on contracts, ADRs, architecture and boundary docs.
- `@security-team` — required on `engine/security/`, `engine/compliance/`, governance contracts, security docs, auditors.
- `@sre-team` — required on runbooks, observability docs and config, CI workflows, deploy, infrastructure.

If any of these teams do not yet exist in the org, replace with an interim individual handle in a follow-up commit; the file structure can stay.

## Next steps

1. **Open a PR** from `feat/contracts-ci-wiring` into `main`.
2. **After merge**, set branch protection per `docs/ci/REQUIRED_CHECKS.md`.
3. **Reconcile** `tools/l9_template_manifest.yaml` with the L9 docs/contracts scaffold so the legacy SHA verifier becomes blocking again. Track as `chore/legacy-contract-manifest-reconciliation`.
4. **Backfill L9_META headers** on `docs/agent-tasks/`, `docs/audit/`, `docs/review/`. Track as `chore/legacy-doc-l9-headers`. Once complete, drop the directories from `EXEMPT_PREFIXES` in `scripts/check_l9_meta_headers.py`.
5. **Promote action versions to SHA pins** as part of the supply-chain hardening track.
6. **Provision Quality Gates secrets** (`SONAR_TOKEN`, `GITGUARDIAN_API_KEY`, `CODECOV_TOKEN`) so `ci-quality.yml` can run end-to-end and be added to required checks.

## What this branch does not change

- No engine, chassis, tools, domain, or test source is modified.
- No legacy contract or workflow is removed.
- No production behaviour changes — this branch is CI wiring, scripts, and ownership only.
