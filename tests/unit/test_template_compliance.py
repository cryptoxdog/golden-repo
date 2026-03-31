from __future__ import annotations

import json
from pathlib import Path

from tools.review.analyzers.template_compliance import run


def test_template_compliance_passes_for_repo() -> None:
    proposal_path = Path("tests/fixtures/review_context.json")
    report = run(Path("."), Path("tools/review/policy/template_manifest.yaml"), proposal_path)
    assert report.verdict == "APPROVE"
    assert report.findings == []


def test_template_compliance_detects_protected_file_modification(tmp_path: Path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "id": "proposal_1",
                "type": "workflow_change",
                "changed_files": [".github/workflows/ai-review.yml"],
                "changed_lines": 1,
                "diff": "diff",
                "metadata": {"base_ref": "origin/main", "head_ref": "HEAD", "source": "git_pr"},
            }
        ),
        encoding="utf-8",
    )
    report = run(Path("."), Path("tools/review/policy/template_manifest.yaml"), proposal_path)
    assert report.verdict == "BLOCK"
    assert any(item.rule_id == "TEMPLATE-003" for item in report.findings)
