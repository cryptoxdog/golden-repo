from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.review.llm.semantic_review import run


def test_semantic_review_emits_suggested_test_for_spec_without_tests(tmp_path: Path) -> None:
    proposal_path = tmp_path / "proposal.json"
    policy_path = tmp_path / "policy.yaml"
    proposal_path.write_text(
        json.dumps(
            {
                "id": "proposal_1",
                "type": "spec_change",
                "changed_files": ["spec.yaml", "engine/services/action_service.py"],
                "changed_lines": 100,
                "diff": "diff",
                "metadata": {
                    "spec_changed": True,
                    "source": "git_pr",
                    "base_ref": "origin/main",
                    "head_ref": "HEAD",
                },
            }
        ),
        encoding="utf-8",
    )
    policy = {"size_limits": {"max_changed_lines_for_semantic_review": 800}}
    policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    report = run(proposal_path, policy_path)
    assert report.verdict == "WARN"
    assert report.suggested_tests
