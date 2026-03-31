# ARCHITECTURE.md

## Repository role

This repository implements a deterministic-first universal change governance engine for L9-aligned engine repositories and includes a minimal example engine used to keep runtime boundary rules testable.

It is not a chassis and it is not a public runtime API service.

## Top-level architecture

```text
git refs / synthetic proposal
  -> tools/review/build_context.py or adapter
  -> ChangeProposal
  -> tools/review/classify_pr.py
  -> deterministic analyzers
  -> tools/review/aggregate.py
  -> GovernanceDecision
  -> workflow enforcement / comment rendering
```

## Subsystems

### Governance control plane: `tools/review/`

Purpose:
- evaluate proposed changes deterministically
- classify risk
- enforce protected-path and architecture rules
- produce final governance decision

Key modules:
- `build_context.py`
- `classify_pr.py`
- `aggregate.py`
- `format_pr_comment.py`
- `waivers.py`
- `evals/replay.py`

Analyzers:
- `template_compliance.py`
- `architecture_boundary.py`
- `protected_paths.py`
- `spec_coverage.py`
- `yaml_validation.py`

Contracts:
- `tools/review/schemas/change_proposal.schema.json`
- `tools/review/schemas/governance_decision.schema.json`

Policies:
- `tools/review/policy/review_policy.yaml`
- `tools/review/policy/architecture.yaml`
- `tools/review/policy/template_manifest.yaml`
- `tools/review/policy/review_exceptions.yaml`

### Example runtime engine: `engine/`

Purpose:
- validate that the repository remains compatible with L9 engine boundaries

Constraints:
- no HTTP routes
- no auth
- no tenancy
- no gateway logic
- `engine/handlers.py` is the only chassis bridge
