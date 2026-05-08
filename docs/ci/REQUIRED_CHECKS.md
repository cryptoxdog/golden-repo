<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: ci
  tags: [ci, branch-protection, required-checks, governance]
  owner: platform
  status: active
-->

# Required CI checks

This document is the source of truth for branch protection on `main`. The
checks listed below are **required status checks**. A pull request cannot be
merged until every required check is green and CODEOWNERS approvals are in
place.

## Required status checks (set in branch protection)

Configure these exactly as named in `Settings → Branches → main → Require
status checks to pass before merging`:

| Check name | Workflow file | Job id |
|---|---|---|
| `Lint & type check` | `.github/workflows/ci.yml` | `lint` |
| `Audit (27 rules)` | `.github/workflows/ci.yml` | `audit` |
| `Tests` | `.github/workflows/ci.yml` | `test` |
| `Compliance (legacy + L9)` | `.github/workflows/ci.yml` | `compliance` |
| `L9 contracts verify (required)` | `.github/workflows/contracts-l9.yml` | `verify` |
| `Protocol conformance (required)` | `.github/workflows/protocol-conformance.yml` | `conformance` |

Optional but strongly recommended:

- `Quality Gates` (from `.github/workflows/ci-quality.yml`) once SonarCloud /
  GitGuardian / Codecov tokens are provisioned.
- `dependency-review`, `sbom`, `slsa-build` for supply-chain assurance.

## Branch-protection settings

Apply these settings on `main`:

- Require a pull request before merging: **enabled**.
- Require approvals: **2**.
- Dismiss stale approvals on new commits: **enabled**.
- Require review from Code Owners: **enabled**.
- Require status checks to pass before merging: **enabled**, "Require
  branches to be up to date before merging" enabled.
- Require conversation resolution before merging: **enabled**.
- Require signed commits: **enabled**.
- Require linear history: **enabled**.
- Lock branch (no force-push, no deletion): **enabled**.

## What each L9 check enforces

### `L9 contracts verify (required)`
Walks `contracts/**/*.contract.yaml` and validates every file against
`contracts/_schemas/l9_contract_meta.schema.json`. Asserts:
- L9_META header present.
- YAML is well-formed and matches the meta-schema.
- No file (other than the migration contract) declares `PacketEnvelope` as
  canonical — TransportPacket is canonical per ADR-0001.

Runs `tools/verify_contracts.py` for the legacy SHA-manifest, then runs
`scripts/validate_contract_alignment.py` against the service manifest.

Finally runs `scripts/check_l9_meta_headers.py` to ensure every doc and
contract carries the L9_META header.

### `Compliance (legacy + L9)`
Same set of contract checks, run as part of the existing CI workflow so that
any PR — even one that does not touch contracts — is held to the
same standard.

### `Protocol conformance (required)`
Validates the canonical contract alignment with the service manifest and
re-runs the L9 meta-schema verifier. Also runs the contract test suite at
`tests/contracts/`.

## Local pre-merge checklist

Run before pushing:

```bash
python scripts/verify_l9_contracts.py
python scripts/check_l9_meta_headers.py
python tools/verify_contracts.py
python scripts/validate_contract_alignment.py --repo-root . \
  --manifest templates/service/service.manifest.yaml
pytest tests/contracts -q
```

All five must exit zero.

## Operational notes

- **Tolerant mode.** `scripts/verify_l9_contracts.py` exits zero when the L9
  meta-schema is absent. This lets the workflow run on `main` cleanly until
  the L9 docs/contracts scaffold PR has merged.
- **Non-fast-forward pushes.** Disabled on `main` by branch protection.
  Submit changes via PR.
- **Workflow pinning.** Action versions in workflows are pinned to major
  versions for the platform team's chosen action set; promote to SHA pins as
  part of the supply-chain hardening track.

## Owners

- Branch-protection configuration: `@platform-team`.
- Required-check authoring: `@platform-team`, `@architecture-team`.
- Quality Gates secrets and variables: `@platform-team`, `@sre-team`.
