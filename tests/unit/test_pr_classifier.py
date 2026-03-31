from __future__ import annotations

import yaml

from tools.review.classify_pr import classify


def test_classifier_escalates_critical_path() -> None:
    policy = yaml.safe_load(open("tools/review/policy/review_policy.yaml", encoding="utf-8").read())
    proposal = {
        "id": "proposal_1",
        "type": "spec_change",
        "changed_files": ["spec.yaml"],
        "changed_lines": 10,
        "diff": "diff",
        "metadata": {
            "spec_changed": True,
            "workflow_changed": False,
            "policy_changed": False,
            "source": "git_pr",
            "base_ref": "origin/main",
            "head_ref": "HEAD",
        },
    }
    result = classify(proposal, policy)
    assert result["risk"] == "critical"
    assert result["run_semantic_review"] is True
    assert result["proposal_id"] == "proposal_1"
