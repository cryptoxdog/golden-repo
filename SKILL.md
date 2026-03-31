# SKILL.md

## Skill name
Operate the Golden Repo AI Review System safely and deterministically.

## When to use this skill
Use this skill when:
- modifying review analyzers
- changing policy or schemas
- updating workflow execution
- adjusting waivers, formatting, or eval replay
- editing root governance/agent-control documentation

## Core facts
- Input contract: `ChangeProposal` — `tools/review/schemas/change_proposal.schema.json`
- Output contract: `GovernanceDecision` — `tools/review/schemas/governance_decision.schema.json`
- Deterministic-first enforcement
- Semantic review is bounded and advisory/escalatory only
- Example engine must remain L9-compatible and free of HTTP/gateway concerns

## Required execution sequence
1. inspect affected modules
2. confirm if change touches protected paths
3. preserve current CLI contracts
4. update docs if runtime or workflow behavior changes
5. run tests
6. run local review flow if review pipeline changed

## Required validation
```bash
make test
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
```

If changing policy or schemas:
```bash
make validate-policy
make eval
```
