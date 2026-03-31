from __future__ import annotations

from tools.review.classify_pr import classify
import yaml


def test_classifier_escalates_critical_path() -> None:
    policy = yaml.safe_load(open("tools/review/policy/review_policy.yaml", encoding="utf-8"))
    context = {
        "changed_files": ["spec.yaml"],
        "changed_lines": 10,
        "spec_changed": True,
    }
    result = classify(context, policy)
    assert result["risk"] == "critical"
    assert result["run_semantic_review"] is True
