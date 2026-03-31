from __future__ import annotations

import json
from pathlib import Path

from tools.review.llm.semantic_review import run


def test_semantic_review_emits_suggested_test_for_spec_without_tests(tmp_path):
    context_path = tmp_path / "context.json"
    policy_path = tmp_path / "policy.yaml"
    context_path.write_text(json.dumps({
        "changed_files": ["spec.yaml", "engine/services/action_service.py"],
        "changed_lines": 100,
        "spec_changed": True,
    }), encoding="utf-8")
    policy_path.write_text("""
size_limits:
  max_changed_lines_for_semantic_review: 800
""", encoding="utf-8")
    # enrich remaining policy fields
    policy_path.write_text("""
size_limits:
  max_changed_lines_for_semantic_review: 800
""", encoding="utf-8")
    import yaml
    policy = {"size_limits": {"max_changed_lines_for_semantic_review": 800}}
    policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    report = run(context_path, policy_path)
    assert report.verdict == "WARN"
    assert report.suggested_tests
