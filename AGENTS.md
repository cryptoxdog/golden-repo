# AGENTS.md

## Mission

Implement and maintain the repository as a deterministic-first governance engine with a minimal example engine. Every change must preserve the current deterministic execution path and protected governance boundaries.

## Agent operating model

### Primary objective
Maintain and improve:
- normalized change intake via `ChangeProposal`
- deterministic review analyzers
- canonical final output via `GovernanceDecision`
- strict separation between governance tooling and runtime engine code

### Secondary objective
Keep the example `engine/` L9-compatible:
- no routes
- no auth
- no tenancy
- no infrastructure logic
- no gateway behavior

## Repository map

### Governance control plane
- `tools/review/build_context.py`
- `tools/review/classify_pr.py`
- `tools/review/aggregate.py`
- `tools/review/format_pr_comment.py`
- `tools/review/waivers.py`
- `tools/review/evals/replay.py`
- `tools/review/analyzers/*`
- `tools/review/llm/*`
- `tools/review/policy/*`
- `tools/review/schemas/*`

### Example engine
- `engine/handlers.py`
- `engine/services/action_service.py`
- `engine/config/*`
- `engine/models/*`
- `engine/core/*`
- `engine/compliance/*`

## Hard execution rules

1. Do not add alternate APIs.
2. Do not add HTTP routes anywhere in `engine/`.
3. Do not move governance logic into `engine/`.
4. Do not import `tools.review` from runtime engine modules.
5. Do not bypass `ChangeProposal` for new review entry points.
6. Do not bypass `GovernanceDecision` for final review results.
7. Do not convert semantic review into autonomous blocking authority.
8. Do not add placeholders, TODOs, or dead files.
9. Keep all output schemas, workflow usage, and Make targets consistent.
10. Update tests for every material change.

## Required file ownership awareness

Protected paths:
- `.github/workflows/**`
- `.github/CODEOWNERS`
- `tools/review/policy/**`
- `tools/review/schemas/**`
- `engine/handlers.py`
- `engine/models/**`
- `spec.yaml`

Changes in those paths must remain deterministic, explicit, and fully tested.

## Safe modification zones

Preferred work areas:
- analyzer internals
- report rendering
- waivers
- eval replay
- tests
- documentation

Higher-risk areas:
- schemas
- aggregate logic
- workflow files
- policy files
- handler contract

## Completion gate

A task is complete only when:
- tests pass
- imports resolve
- affected workflows still match actual CLI contracts
- docs remain consistent with the real repo behavior
