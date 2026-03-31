# TESTING.md

## Test structure

```
tests/
├── unit/               # Per-module unit tests
├── integration/        # End-to-end review pipeline tests
└── fixtures/
    └── eval_cases.json # Synthetic eval cases for replay
```

## Running tests

```bash
make test
```

Equivalent to:
```bash
python -m pytest
```

## Running the full local review flow
```bash
make review-local BASE_REF=HEAD~1 HEAD_REF=HEAD
```

Artifacts written to `.artifacts/review/`.

## Validating policy
```bash
make validate-policy
```

## Running eval replay
```bash
make eval
```

Output written to `.artifacts/evals/eval_results.json`.

## Coverage requirements

Every behavior change must have corresponding test coverage in:
- `tests/unit/` for new or modified modules
- `tests/integration/` for changes to the review pipeline or aggregation logic

## Linting and type checking

```bash
make lint
make typecheck
```

These are optional for normal development but required before any schema or policy change.

## CI behavior

The `ci.yml` workflow runs `make test` on every push and PR.
The `ai-review.yml` workflow runs the full deterministic review pipeline on PRs.
