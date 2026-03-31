from __future__ import annotations

import json
from pathlib import Path

from tools.review.analyzers.architecture_boundary import run


def test_architecture_validator_passes_for_handlers_file(tmp_path: Path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "id": "proposal_1",
                "type": "code_change",
                "changed_files": ["engine/handlers.py"],
                "changed_lines": 1,
                "diff": "diff",
                "metadata": {"base_ref": "origin/main", "head_ref": "HEAD", "source": "git_pr"},
            }
        ),
        encoding="utf-8",
    )
    report = run(Path("."), Path("tools/review/policy/architecture.yaml"), proposal_path)
    assert report.verdict == "APPROVE"


def test_architecture_validator_detects_forbidden_import(tmp_path: Path) -> None:
    bad_file = Path("engine/services/_temporary_bad_import.py")
    bad_file.write_text("from engine.handlers import handle_execute\n", encoding="utf-8")
    try:
        proposal_path = tmp_path / "proposal.json"
        proposal_path.write_text(
            json.dumps(
                {
                    "id": "proposal_1",
                    "type": "code_change",
                    "changed_files": ["engine/services/_temporary_bad_import.py"],
                    "changed_lines": 1,
                    "diff": "diff",
                    "metadata": {"base_ref": "origin/main", "head_ref": "HEAD", "source": "git_pr"},
                }
            ),
            encoding="utf-8",
        )
        report = run(Path("."), Path("tools/review/policy/architecture.yaml"), proposal_path)
        assert report.verdict == "BLOCK"
        assert any(item.rule_id == "ARCH-IMPORT-001" for item in report.findings)
    finally:
        bad_file.unlink(missing_ok=True)
