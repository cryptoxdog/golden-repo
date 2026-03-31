# CLAUDE.md

This repository implements an **L9-aligned universal change governance engine** for engine repositories. It is not a runtime API service and it is not a chassis. It evaluates repository change proposals against deterministic policy, architecture, template, and spec constraints, then emits a governance decision.

## Repository purpose

The repository has two active subsystems:

1. **engine/** - Minimal example engine code used to validate L9 chassis/engine boundaries.
   - Exposes only `execute` and `handle_describe` through `engine/handlers.py`.
   - Does not own HTTP routes, auth, rate limiting, tenancy, logging config, or gateway concerns.

2. **tools/review/** - Deterministic-first change governance subsystem.
   - Converts git/PR input into a normalized `ChangeProposal`.
   - Runs classifier + analyzers.
   - Emits a normalized `GovernanceDecision`.
   - Supports waivers, semantic escalation, PR comment formatting, and eval replay.

## Non-negotiable architecture rules

- Treat `tools/review/` as the governance control plane.
- Treat `engine/` as example runtime domain logic only.
- Do not introduce FastAPI, Starlette, uvicorn, gateway, auth, or route code into `engine/`.
- `engine/handlers.py` is the only chassis bridge.
- `tools/review/` must not be imported by runtime engine code.
- The review core must consume normalized proposals, not raw PR assumptions.
- The final output contract is `GovernanceDecision`, not ad hoc report JSON.
- Changes to `.github/workflows/**` and `tools/review/policy/**` are protected and must remain deterministic-first.

## Runtime and execution model

### Deterministic review path
1. `tools/review/build_context.py` creates `ChangeProposal`
2. `tools/review/classify_pr.py` computes risk + semantic trigger
3. Deterministic analyzers run:
   - `architecture_boundary.py`
   - `protected_paths.py`
   - `spec_coverage.py`
   - `yaml_validation.py`
4. `tools/review/aggregate.py` emits `GovernanceDecision`
5. `tools/review/format_pr_comment.py` renders human-readable output
6. Optional `llm/semantic_review.py` adds advisory/escalation signal

### Core contracts
- Input: `tools/review/schemas/change_proposal.schema.json`
- Output: `tools/review/schemas/governance_decision.schema.json`

## Required development behavior

When modifying this repo:
- keep changes additive and non-breaking
- preserve existing CLI signatures where already used by workflows
- update tests in `tests/unit/` and `tests/integration/` with every behavior change
- prefer deterministic enforcement over semantic inference
- never let semantic review become the sole blocking authority

## Required local verification

Run before considering work complete:

```bash
make test
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
```

If changing policy or contracts, also run:

```bash
make validate-policy
python tools/review/evals/replay.py \
  --cases tests/fixtures/eval_cases.json \
  --policy tools/review/policy/review_policy.yaml \
  --output /tmp/eval_results.json
```
