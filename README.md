# Golden Repo AI Review System v2

Deterministic-first review subsystem for L9-aligned engine repositories.

## Included capabilities

- PR context construction from git
- PR classification and risk routing
- deterministic blocking analyzers
- protected path escalation
- spec coverage enforcement
- YAML and schema validation
- aggregate decision engine
- waiver support
- PR comment formatter
- semantic escalation with suggested tests
- historical evaluation harness

## Local workflow

```bash
python tools/review/build_context.py --base-ref HEAD~1 --head-ref HEAD --output review_context.json
python tools/review/classify_pr.py --base-ref HEAD~1 --head-ref HEAD --policy tools/review/policy/review_policy.yaml --output pr_classification.json
python tools/review/analyzers/template_compliance.py --repo-root . --manifest tools/review/policy/template_manifest.yaml --context review_context.json --output template_report.json
python tools/review/analyzers/architecture_boundary.py --repo-root . --architecture tools/review/policy/architecture.yaml --context review_context.json --output architecture_report.json
python tools/review/analyzers/spec_coverage.py --repo-root . --spec spec.yaml --output spec_coverage_report.json
python tools/review/aggregate.py --reports template_report.json architecture_report.json spec_coverage_report.json --policy tools/review/policy/review_policy.yaml --output final_verdict.json
python tools/review/format_pr_comment.py --report final_verdict.json --output pr_comment.md
```

## Waivers

Edit `tools/review/policy/review_exceptions.yaml` to define time-bounded exceptions by
`rule_id` and `file_pattern`.

## Evals

Replay historical or synthetic review cases with:

```bash
python tools/review/evals/replay.py   --cases tests/fixtures/eval_cases.json   --policy tools/review/policy/review_policy.yaml   --output eval_results.json
```
