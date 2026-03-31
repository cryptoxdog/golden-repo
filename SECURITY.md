# SECURITY.md

## Scope
This repository governs repository changes. Security sensitivity is concentrated in:
- policy files
- schemas
- workflow files
- aggregation logic
- waiver handling
- comment/report generation
- example engine handler and model boundaries

## Reporting a vulnerability
Report issues affecting:
- protected path enforcement
- waiver bypass
- architecture boundary bypass
- schema validation bypass
- workflow contract mismatch
- analyzer result spoofing
- aggregate decision corruption

Use a private disclosure channel appropriate to your environment. Do not open a public issue containing exploit details.

## Security model

### Deterministic-first
The system must prefer deterministic checks over semantic inference.

### Protected paths
Changes to:
- `.github/workflows/**`
- `.github/CODEOWNERS`
- `tools/review/policy/**`
- `tools/review/schemas/**`
- `engine/handlers.py`
- `engine/models/**`
- `spec.yaml`

must be treated as high-sensitivity.

### Waivers
Waivers are explicit, time-bounded, and rule/file scoped. They must not become open-ended suppression.

### Engine boundary
The example engine must not acquire:
- HTTP routes
- auth
- rate limiting
- tenancy resolution
- gateway logic

### Semantic review
Semantic review must remain bounded and non-sovereign.

## Minimum verification for sensitive changes
```bash
make test
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
make validate-policy
make eval
```
