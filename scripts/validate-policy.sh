#!/usr/bin/env bash
set -euo pipefail
python tools/review/analyzers/yaml_validation.py --policy tools/review/policy/review_policy.yaml --output yaml_validation_report.json
cat yaml_validation_report.json
