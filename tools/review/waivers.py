from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class WaiverEntry:
    waiver_id: str
    rule_id: str
    file_pattern: str
    reason: str
    owner: str
    expires_on: str


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exceptions": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"exceptions": []}


def load_waivers(path: str | Path) -> list[WaiverEntry]:
    payload = _load_yaml(Path(path))
    waivers: list[WaiverEntry] = []
    for entry in payload.get("exceptions", []):
        waivers.append(
            WaiverEntry(
                waiver_id=entry["id"],
                rule_id=entry["rule_id"],
                file_pattern=entry["file_pattern"],
                reason=entry["reason"],
                owner=entry["owner"],
                expires_on=entry["expires_on"],
            )
        )
    return waivers


def is_active(waiver: WaiverEntry, now: datetime | None = None) -> bool:
    ts = now or datetime.now(tz=UTC)
    expiry = datetime.fromisoformat(f"{waiver.expires_on}T23:59:59+00:00")
    return ts <= expiry


def match_waiver(finding: dict[str, Any], waivers: list[WaiverEntry]) -> WaiverEntry | None:
    for waiver in waivers:
        if not is_active(waiver):
            continue
        if finding.get("rule_id") != waiver.rule_id:
            continue
        if fnmatch(finding.get("file", ""), waiver.file_pattern):
            return waiver
    return None
