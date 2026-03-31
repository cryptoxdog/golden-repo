from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Finding:
    file: str
    line: int
    severity: str
    rule_id: str
    finding: str


@dataclass(slots=True)
class ReviewReport:
    dimension: str
    verdict: str
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    rationale_summary: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(item) for item in self.findings]
        return payload

    def write(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
