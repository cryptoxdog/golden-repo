from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import json
from typing import Any


@dataclass(slots=True)
class Finding:
    file: str
    line: int
    severity: str
    rule_id: str
    finding: str
    waived: bool = False
    waiver_reason: str | None = None


@dataclass(slots=True)
class SuggestedTest:
    name: str
    file: str
    purpose: str
    assertion: str


@dataclass(slots=True)
class ReviewReport:
    dimension: str
    verdict: str
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    rationale_summary: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    suggested_tests: list[SuggestedTest] = field(default_factory=list)
    repro_steps: list[str] = field(default_factory=list)
    waived_findings: list[Finding] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(item) for item in self.findings]
        payload["suggested_tests"] = [asdict(item) for item in self.suggested_tests]
        payload["waived_findings"] = [asdict(item) for item in self.waived_findings]
        return payload

    def write(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def load_json_report(path: str | Path) -> dict | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))
