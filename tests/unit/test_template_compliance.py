from __future__ import annotations

import json
from pathlib import Path

from tools.review.analyzers.template_compliance import run


def test_template_compliance_passes_for_repo() -> None:
    context_path = Path("tests/fixtures/review_context.json")
    report = run(Path("."), Path("tools/review/policy/template_manifest.yaml"), context_path)
    assert report.verdict == "APPROVE"
    assert report.findings == []


def test_template_compliance_detects_protected_file_modification(tmp_path: Path) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text(
        json.dumps({"changed_files": [".github/workflows/ai-review.yml"]}),
        encoding="utf-8",
    )
    report = run(Path("."), Path("tools/review/policy/template_manifest.yaml"), context_path)
    assert report.verdict == "BLOCK"
    assert any(item.rule_id == "TEMPLATE-003" for item in report.findings)
