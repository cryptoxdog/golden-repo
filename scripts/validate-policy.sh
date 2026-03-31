#!/usr/bin/env bash
set -euo pipefail
python tools/review/analyzers/yaml_validation.py   --policy tools/review/policy/review_policy.yaml   --output /tmp/yaml_validation_report.json
cat /tmp/yaml_validation_report.json
