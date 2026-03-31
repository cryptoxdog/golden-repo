# GUARDRAILS.md

## Governance guardrails

### Deterministic-first
All enforcement decisions must pass through deterministic analyzers before semantic review is considered. Semantic review is advisory and escalatory — it may never be the sole blocking authority.

### Contract preservation
- `ChangeProposal` is the only normalized governance input.
- `GovernanceDecision` is the only normalized final governance output.
- No ad hoc JSON structures may replace or bypass these contracts.

### Engine boundary
`engine/` must remain free of:
- HTTP routes
- auth logic
- rate limiting
- tenancy resolution
- gateway behavior
- direct imports of `tools/review/`

### Protected path enforcement
Changes to protected paths must:
- pass deterministic analyzer checks
- have explicit waiver if excepted
- be reviewed by CODEOWNERS

### Waiver discipline
Waivers must be:
- explicit (named rule + named file/path)
- time-bounded (expiry date required)
- policy-driven (declared in `review_exceptions.yaml`)
- not open-ended suppression

### Semantic review scope
`llm/semantic_review.py`:
- runs only when triggered by classifier policy
- contributes advisory signal only
- cannot override a deterministic BLOCK verdict

### Workflow contract integrity
GitHub workflow YAML must match actual CLI signatures of invoked scripts.
Any argument change requires simultaneous update of:
- workflow YAML
- Makefile
- README.md
- CLAUDE.md
- TESTING.md
