from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


VERDICT_PRIORITY = {
    "BLOCK": 4,
    "ESCALATE": 3,
    "WARN": 2,
    "APPROVE": 1,
}


def load_report(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate_reports(reports: list[dict], policy: dict) -> dict:
    blocking_checks = set(policy["blocking_checks"])
    advisory_checks = set(policy["advisory_checks"])

    final_verdict = "APPROVE"
    rationale_summary: list[str] = []
    findings: list[dict] = []

    for report in reports:
        if not report:
            continue
        dimension = report.get("dimension", "aggregate")
        verdict = report.get("verdict", "APPROVE")
        report_findings = report.get("findings", [])
        findings.extend(report_findings)
        rationale_summary.extend(report.get("rationale_summary", []))

        if dimension in blocking_checks and verdict == "BLOCK":
            final_verdict = "BLOCK"
        elif dimension in advisory_checks and verdict == "ESCALATE" and final_verdict != "BLOCK":
            final_verdict = "ESCALATE"
        elif verdict == "WARN" and final_verdict == "APPROVE":
            final_verdict = "WARN"

    confidence = min((report.get("confidence", 1.0) for report in reports if report), default=1.0)

    return {
        "dimension": "aggregate",
        "final_verdict": final_verdict,
        "confidence": confidence,
        "findings": findings,
        "rationale_summary": rationale_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    reports = [load_report(Path(item)) for item in args.reports]
    payload = aggregate_reports([item for item in reports if item is not None], policy)
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
