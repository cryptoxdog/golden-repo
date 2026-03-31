from __future__ import annotations

import json
from pathlib import Path

from tools.review.analyzers.architecture_boundary import run


def test_architecture_validator_passes_for_handlers_file(tmp_path: Path) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps({"changed_files": ["engine/handlers.py"]}), encoding="utf-8")
    report = run(Path("."), Path("tools/review/policy/architecture.yaml"), context_path)
    assert report.verdict == "APPROVE"


def test_architecture_validator_detects_forbidden_import(tmp_path: Path) -> None:
    bad_file = Path("engine/services/_temporary_bad_import.py")
    bad_file.write_text("from engine.handlers import handle_execute\n", encoding="utf-8")
    try:
        context_path = tmp_path / "context.json"
        context_path.write_text(
            json.dumps({"changed_files": ["engine/services/_temporary_bad_import.py"]}),
            encoding="utf-8",
        )
        report = run(Path("."), Path("tools/review/policy/architecture.yaml"), context_path)
        assert report.verdict == "BLOCK"
        assert any(item.rule_id == "ARCH-IMPORT-001" for item in report.findings)
    finally:
        bad_file.unlink(missing_ok=True)
