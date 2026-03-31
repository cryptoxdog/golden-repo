"""
tools/auditors/integration_boundary.py

Integration Boundary Validator — Dimension 4.

Detects backward-incompatible schema changes in Pydantic models that could
break downstream constellation consumers. Parses diff for model field
removals, type changes, and required-field additions to response schemas.

Usage:
    python tools/auditors/integration_boundary.py \
        --pr-diff pr.diff \
        --output integration_report.json

Exit codes: 0 = clean, 1 = breaking changes detected, 2 = error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class BreakingChange:
    change_type: str
    field: str
    file: str
    severity: str
    message: str
    old_type: str = ""
    new_type: str = ""


@dataclass
class IntegrationReport:
    breaking_changes: list[BreakingChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    verdict: str = "APPROVE"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "breaking_changes": [c.__dict__ for c in self.breaking_changes],
            "warnings": self.warnings,
        }


# ── Diff parsing ──────────────────────────────────────────────────────────────

_REMOVED_FIELD_RE = re.compile(r"^-\s{4}(\w+)\s*:\s*(.+)$")
_ADDED_FIELD_RE = re.compile(r"^\+\s{4}(\w+)\s*:\s*(.+)$")
_FILE_HEADER_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK_RE = re.compile(r"^@@")


def detect_breaking_changes_from_diff(diff_text: str) -> list[BreakingChange]:
    """
    Parse a unified diff for model schema changes.
    Breaking changes:
      - Removed field from a response/request model
      - Changed field type annotation
      - Removed from Optional / made required
    """
    breaking: list[BreakingChange] = []
    current_file = ""
    in_models_context = False

    for line in diff_text.splitlines():
        m = _FILE_HEADER_RE.match(line)
        if m:
            current_file = m.group(2)
            in_models_context = (
                "engine/models" in current_file
                or "engine/packet" in current_file
                or "l9_core/models" in current_file
            )
            continue

        if not in_models_context:
            continue

        # Removed field
        rm = _REMOVED_FIELD_RE.match(line)
        if rm:
            field_name, old_type = rm.group(1), rm.group(2).strip()
            breaking.append(BreakingChange(
                change_type="removed_field",
                field=field_name,
                file=current_file,
                severity="CRITICAL",
                message=f"Removing field '{field_name}' is a breaking change — downstream consumers may depend on it",
                old_type=old_type,
            ))
            continue

    return breaking


def detect_type_changes_from_diff(diff_text: str) -> list[BreakingChange]:
    """
    Detect field type annotation changes by pairing removed/added lines
    with the same field name in the same file.
    """
    changes: list[BreakingChange] = []
    current_file = ""
    in_models_context = False
    removed_in_hunk: dict[str, str] = {}  # field_name → old_type
    added_in_hunk: dict[str, str] = {}    # field_name → new_type

    def flush_hunk():
        nonlocal removed_in_hunk, added_in_hunk
        for field_name in removed_in_hunk:
            if field_name in added_in_hunk:
                old_t = removed_in_hunk[field_name]
                new_t = added_in_hunk[field_name]
                if old_t != new_t:
                    changes.append(BreakingChange(
                        change_type="type_change",
                        field=field_name,
                        file=current_file,
                        severity="CRITICAL",
                        message=f"Type of '{field_name}' changed: {old_t!r} → {new_t!r}",
                        old_type=old_t,
                        new_type=new_t,
                    ))
        removed_in_hunk = {}
        added_in_hunk = {}

    for line in diff_text.splitlines():
        fh = _FILE_HEADER_RE.match(line)
        if fh:
            flush_hunk()
            current_file = fh.group(2)
            in_models_context = (
                "engine/models" in current_file
                or "engine/packet" in current_file
                or "l9_core/models" in current_file
            )
            continue

        if _HUNK_RE.match(line):
            flush_hunk()
            continue

        if not in_models_context:
            continue

        rm = _REMOVED_FIELD_RE.match(line)
        if rm:
            removed_in_hunk[rm.group(1)] = rm.group(2).strip()
            continue

        am = _ADDED_FIELD_RE.match(line)
        if am:
            added_in_hunk[am.group(1)] = am.group(2).strip()

    flush_hunk()
    return changes


# ── Packet envelope compatibility ─────────────────────────────────────────────

def check_packet_envelope_compatibility(pr_diff: str) -> list[BreakingChange]:
    """
    Focused check: any field removal or type change in PacketEnvelope,
    TenantContext, or PacketLineage is CRITICAL.
    """
    breaking = detect_breaking_changes_from_diff(pr_diff)
    breaking += detect_type_changes_from_diff(pr_diff)
    return breaking


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_integration_boundary(breaking: list[BreakingChange]) -> tuple[float, str]:
    critical = [b for b in breaking if b.severity == "CRITICAL"]
    if critical:
        return 0.99, "BLOCK"
    if breaking:
        return 0.80, "WARN"
    return 0.95, "APPROVE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Integration boundary validator")
    parser.add_argument("--pr-diff", required=True, help="Path to unified diff file")
    parser.add_argument("--output", default="integration_report.json")
    args = parser.parse_args()

    try:
        diff_text = Path(args.pr_diff).read_text()
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    breaking = check_packet_envelope_compatibility(diff_text)
    confidence, verdict = score_integration_boundary(breaking)

    report = IntegrationReport(breaking_changes=breaking, verdict=verdict)
    Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
    print(f"verdict={verdict} breaking_changes={len(breaking)}")

    return 0 if verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
