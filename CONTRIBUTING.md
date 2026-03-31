# CONTRIBUTING.md

## Contribution standard

All changes must be:
- deterministic
- additive and non-breaking unless explicitly approved
- fully wired
- fully tested
- aligned to actual repository behavior

## Before changing code

### Check whether you are changing:
- governance core (`tools/review/*`)
- runtime example engine (`engine/*`)
- protected governance files (`.github/workflows/**`, `.github/CODEOWNERS`, `tools/review/policy/**`, `tools/review/schemas/**`)
- documentation that defines execution behavior

### If yes
You must update any affected:
- tests
- Make targets
- workflow CLI invocations
- root governance documents

## Branch quality gate
A contribution is acceptable only if:
- imports resolve
- no placeholders or TODOs are introduced
- current workflows remain accurate
- all changed behavior is covered by tests

## Local checks
```bash
make test
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
```

Optional quality checks:
```bash
make lint
make typecheck
make validate-policy
make eval
```

## Documentation consistency rule

If you change:
- CLI arguments
- schema fields
- workflow invocations
- analyzer names
- protected path behavior

you must update:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `TESTING.md`
- `ARCHITECTURE.md`
- `GUARDRAILS.md`
