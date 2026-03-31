from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.review.aggregate import aggregate_reports, main as aggregate_main
from tools.review.format_pr_comment import build_comment


def test_aggregate_applies_waiver(tmp_path, monkeypatch):
    policy_path = tmp_path / "review_policy.yaml"
    exceptions_path = tmp_path / "review_exceptions.yaml"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "out.json"

    policy_path.write_text(yaml.safe_dump({
        "blocking_checks": ["template_compliance"],
        "advisory_checks": ["semantic_review"],
        "waivers": {"file": str(exceptions_path)},
    }), encoding="utf-8")
    exceptions_path.write_text(yaml.safe_dump({
        "exceptions": [{
            "id": "WAIVER-1",
            "rule_id": "TEMPLATE-003",
            "file_pattern": ".github/workflows/ai-review.yml",
            "reason": "temporary approved exception",
            "owner": "platform-team",
            "expires_on": "2099-12-31",
        }]
    }), encoding="utf-8")
    report_path.write_text(json.dumps({
        "dimension": "template_compliance",
        "verdict": "BLOCK",
        "confidence": 0.99,
        "findings": [{
            "file": ".github/workflows/ai-review.yml",
            "line": 1,
            "severity": "critical",
            "rule_id": "TEMPLATE-003",
            "finding": "Protected template file was modified",
        }],
        "rationale_summary": ["x"],
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "aggregate.py",
        "--reports", str(report_path),
        "--policy", str(policy_path),
        "--output", str(output_path),
    ])
    aggregate_main()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["final_verdict"] == "APPROVE"
    assert len(payload["waived_findings"]) == 1


def test_pr_comment_formatter_includes_suggested_tests():
    comment = build_comment({
        "final_verdict": "WARN",
        "rationale_summary": ["Example rationale"],
        "findings": [],
        "suggested_tests": [{
            "name": "test_example",
            "file": "tests/unit/test_example.py",
            "purpose": "protect behavior",
            "assertion": "assert result == expected",
        }],
    })
    assert "Suggested Tests" in comment
    assert "test_example" in comment
