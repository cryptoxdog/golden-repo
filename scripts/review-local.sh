#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${1:-HEAD~1}"
HEAD_REF="${2:-HEAD}"

python tools/review/build_context.py --base-ref "$BASE_REF" --head-ref "$HEAD_REF" --output review_context.json
python tools/review/classify_pr.py --base-ref "$BASE_REF" --head-ref "$HEAD_REF" --policy tools/review/policy/review_policy.yaml --output pr_classification.json
python tools/review/analyzers/template_compliance.py --repo-root . --manifest tools/review/policy/template_manifest.yaml --context review_context.json --output template_report.json
python tools/review/analyzers/architecture_boundary.py --repo-root . --architecture tools/review/policy/architecture.yaml --context review_context.json --output architecture_report.json
python tools/review/analyzers/protected_paths.py --policy tools/review/policy/review_policy.yaml --context review_context.json --output protected_paths_report.json
python tools/review/analyzers/spec_coverage.py --repo-root . --spec spec.yaml --output spec_coverage_report.json
python tools/review/analyzers/yaml_validation.py --policy tools/review/policy/review_policy.yaml --output yaml_validation_report.json
python tools/review/aggregate.py --reports template_report.json architecture_report.json protected_paths_report.json spec_coverage_report.json yaml_validation_report.json --policy tools/review/policy/review_policy.yaml --output final_verdict.json

cat final_verdict.json
