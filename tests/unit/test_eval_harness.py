from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.review.evals.replay import evaluate, load_cases


def test_eval_harness_replays_cases(tmp_path):
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({
        "cases": [{
            "name": "clean approve",
            "expected_final_verdict": "APPROVE",
            "reports": [{
                "dimension": "template_compliance",
                "verdict": "APPROVE",
                "confidence": 0.99,
                "findings": [],
                "rationale_summary": ["ok"],
            }]
        }]
    }), encoding="utf-8")
    cases = load_cases(cases_path)
    policy = {"blocking_checks": ["template_compliance"], "advisory_checks": []}
    result = evaluate(cases, policy)
    assert result["passed_count"] == 1
