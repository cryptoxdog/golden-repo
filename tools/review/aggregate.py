from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from tools.review.report import load_json_report
from tools.review.waivers import load_waivers, match_waiver


def _severity_rank(verdict: str) -> int:
    return {
        "BLOCK": 4,
        "ESCALATE": 3,
        "WARN": 2,
        "APPROVE": 1,
    }.get(verdict, 0)


def _apply_waivers(report: dict[str, Any], waivers_path: Path) -> dict[str, Any]:
    waivers = load_waivers(waivers_path)
    active_findings: list[dict[str, Any]] = []
    waived_findings: list[dict[str, Any]] = list(report.get("waived_findings", []))

    for finding in report.get("findings", []):
        waiver = match_waiver(finding, waivers)
        if waiver is None:
            active_findings.append(finding)
            continue
        finding = dict(finding)
        finding["waived"] = True
        finding["waiver_reason"] = waiver.reason
        waived_findings.append(finding)

    report = dict(report)
    report["findings"] = active_findings
    report["waived_findings"] = waived_findings
    if report.get("verdict") in {"BLOCK", "ESCALATE", "WARN"} and not active_findings:
        report["verdict"] = "APPROVE"
    elif report.get("verdict") == "BLOCK" and not any(item.get("severity") == "critical" for item in active_findings):
        report["verdict"] = "ESCALATE" if active_findings else "APPROVE"
    return report


def aggregate_reports(reports: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    blocking_checks = set(policy["blocking_checks"])
    advisory_checks = set(policy["advisory_checks"])

    final_verdict = "APPROVE"
    findings: list[dict[str, Any]] = []
    waived_findings: list[dict[str, Any]] = []
    rationale_summary: list[str] = []
    suggested_tests: list[dict[str, Any]] = []
    repro_steps: list[str] = []

    for report in reports:
        dimension = report.get("dimension", "aggregate")
        verdict = report.get("verdict", report.get("final_verdict", "APPROVE"))
        findings.extend(report.get("findings", []))
        waived_findings.extend(report.get("waived_findings", []))
        rationale_summary.extend(report.get("rationale_summary", []))
        suggested_tests.extend(report.get("suggested_tests", []))
        repro_steps.extend(report.get("repro_steps", []))

        if dimension in blocking_checks and verdict == "BLOCK":
            final_verdict = "BLOCK"
        elif (
            dimension in blocking_checks
            and verdict == "ESCALATE"
            and final_verdict != "BLOCK"
        ):
            final_verdict = "ESCALATE"
        elif (
            dimension in advisory_checks
            and verdict == "ESCALATE"
            and final_verdict not in {"BLOCK", "ESCALATE"}
        ):
            final_verdict = "ESCALATE"
        elif verdict == "WARN" and final_verdict == "APPROVE":
            final_verdict = "WARN"

    confidence = min((report.get("confidence", 1.0) for report in reports), default=1.0)

    return {
        "dimension": "aggregate",
        "final_verdict": final_verdict,
        "confidence": confidence,
        "findings": findings,
        "waived_findings": waived_findings,
        "rationale_summary": rationale_summary,
        "suggested_tests": suggested_tests,
        "repro_steps": repro_steps,
        "metrics": {
            "report_count": len(reports),
            "finding_count": len(findings),
            "waived_finding_count": len(waived_findings),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path(args.policy)
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    waivers_path = policy_path.parent / Path(policy["waivers"]["file"]).name

    reports = []
    for item in args.reports:
        report = load_json_report(item)
        if report is None:
            continue
        reports.append(_apply_waivers(report, waivers_path))
    payload = aggregate_reports(reports, policy)
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
