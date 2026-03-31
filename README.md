# Golden Repo AI Review System

A deterministic-first universal change governance engine for L9-aligned engine repositories.

This repository evaluates proposed repository changes against:
- template constraints
- architecture boundaries
- protected governance paths
- spec coverage
- YAML/schema validity
- optional semantic escalation

It emits a canonical `GovernanceDecision` and is designed to evolve from repository-local PR review into a broader L9 control-plane governance primitive.

## What is in this repository

### 1. Example L9 engine
The `engine/` package is intentionally small. It exists to enforce and validate L9 runtime boundaries:
- `engine/handlers.py` registers `execute` and `describe`
- `engine/services/action_service.py` performs simple action execution
- `engine/config/loader.py` and `engine/config/schema.py` load and validate spec data
- `engine/compliance/prohibited_factors.py` blocks forbidden payload keys
- `engine/models/action_models.py` validates handler payloads

The engine is not an HTTP service. It does not define routes or own auth, rate limiting, tenancy, or logging configuration.

### 2. Governance control plane
The `tools/review/` package implements the actual review system:
- `build_context.py` generates a normalized `ChangeProposal`
- `classify_pr.py` classifies risk and semantic review triggers
- `analyzers/*` generate deterministic review findings
- `aggregate.py` emits a normalized `GovernanceDecision`
- `waivers.py` applies time-bounded exceptions
- `format_pr_comment.py` renders decision output
- `evals/replay.py` replays historical/synthetic review cases
- `llm/semantic_review.py` performs bounded advisory semantic review

## Contracts

### Input contract (`ChangeProposal`)
Location: `tools/review/schemas/change_proposal.schema.json`

Key fields:
- `id`
- `type`
- `changed_files`
- `changed_lines`
- `diff`
- `metadata`

### Output contract (`GovernanceDecision`)
Location: `tools/review/schemas/governance_decision.schema.json`

Key fields:
- `proposal_id`
- `final_verdict`
- `risk`
- `findings`
- `waived_findings`
- `rationale_summary`
- `confidence`
- `trace`

## Deterministic execution path

```text
git refs
  -> tools/review/build_context.py
  -> ChangeProposal
  -> tools/review/classify_pr.py
  -> deterministic analyzers
  -> tools/review/aggregate.py
  -> GovernanceDecision
  -> tools/review/format_pr_comment.py
```

Optional semantic review runs only when triggered by policy and never replaces deterministic enforcement.

## Repository structure

| Path | Purpose |
|---|---|
| `engine/` | Minimal example L9 engine |
| `tools/review/` | Governance control plane |
| `tools/review/policy/` | Policy, architecture, manifest, waivers |
| `tools/review/schemas/` | ChangeProposal + GovernanceDecision schemas |
| `tests/` | Unit + integration coverage |
| `.github/workflows/` | CI and review automation |

## Local development

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests
```bash
make test
```

### Run the local deterministic review flow
```bash
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
```

Artifacts written to `.artifacts/review/`:
- `review_context.json`
- `pr_classification.json`
- analyzer reports
- `final_verdict.json`
- `pr_comment.md`

### Validate policy and schemas
```bash
make validate-policy
```

## CI / workflow behavior

### `ci.yml`
Runs:
- editable install
- unit + integration tests

### `ai-review.yml`
Runs:
- PR classification
- deterministic analyzers
- aggregation
- optional semantic review
- final verdict enforcement

The workflow consumes the same CLI contracts documented in this README and encoded in the Makefile.

## Protected governance paths

The following are high-sensitivity paths protected by CODEOWNERS and policy:
- `.github/workflows/**`
- `.github/CODEOWNERS`
- `tools/review/policy/**`
- `tools/review/schemas/**`
- `engine/handlers.py`
- `engine/models/**`
- `spec.yaml`

## Roadmap posture

This repository is already structured around the first critical generalization:
- internal review logic consumes normalized `ChangeProposal`
- final output is normalized `GovernanceDecision`

That keeps the evaluator core source-agnostic and allows PR ingestion to remain only one adapter path.

## License

See `LICENSE`.
