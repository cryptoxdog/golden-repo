# Review System

The review system is deterministic-first and policy-driven.

## Stages

1. Build review context from git diff.
2. Classify the PR and determine risk.
3. Run deterministic analyzers:
   - template compliance
   - architecture boundary
   - protected paths
   - spec coverage
   - YAML validation
4. Aggregate deterministic results.
5. Optionally run semantic review.
6. Apply waivers during final aggregation.
7. Format a PR comment artifact.

## Outputs

- `review_context.json`
- per-analyzer review reports
- `final_verdict.json`
- `pr_comment.md`
