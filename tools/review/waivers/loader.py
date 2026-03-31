from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Waiver:
    rule_id: str
    file_pattern: str
    reason: str


def load_waivers(waivers_path: Path) -> list[Waiver]:
    """Load waivers from YAML file. Returns empty list if file does not exist."""
    if not waivers_path.exists():
        return []
    data = yaml.safe_load(waivers_path.read_text(encoding="utf-8")) or {}
    return [
        Waiver(
            rule_id=entry["rule_id"],
            file_pattern=entry.get("file_pattern", "*"),
            reason=entry.get("reason", ""),
        )
        for entry in data.get("waivers", [])
    ]


def match_waiver(finding: dict[str, Any], waivers: list[Waiver]) -> Waiver | None:
    """Return the first matching waiver for a finding, or None."""
    rule_id = finding.get("rule_id", "")
    file_path = finding.get("file", "")
    for waiver in waivers:
        if waiver.rule_id == rule_id and fnmatch(file_path, waiver.file_pattern):
            return waiver
    return None
