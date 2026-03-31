from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from tools.review.report import load_json_report
from tools.review.waivers import load_waivers, match_waiver

SEVERITY_TO_RISK = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}


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
    elif report.get("verdict") == "BLOCK" and not any(
        item.get("severity") == "critical" for item in active_findings
    ):
        report["verdict"] = "ESCALATE" if active_findings else "APPROVE"
    return report


def _derive_risk(reports: list[dict[str, Any]]) -> str:
    current = "low"
    for report in reports:
        for finding in report.get("findings", []):
            sev = finding.get("severity", "low")
            if sev == "critical":
                return "critical"
            if sev == "high":
                current = "high"
            elif sev == "medium" and current not in {"high", "critical"}:
                current = "medium"
    return current


def aggregate_reports(
    reports: list[dict[str, Any]],
    policy: dict[str, Any],
    proposal_id: str = "unknown_proposal",
    source_report_files: list[str] | None = None,
) -> dict[str, Any]:
    waivers_path = Path(
        policy.get("waivers", {}).get("file", "tools/review/policy/review_exceptions.yaml")
    )
    resolved_reports = [_apply_waivers(report, waivers_path) for report in reports]

    blocking_checks = set(policy["blocking_checks"])
    advisory_checks = set(policy.get("advisory_checks", []))

    final_verdict = "APPROVE"
    confidence = 0.99
    findings: list[dict[str, Any]] = []
    waived_findings: list[dict[str, Any]] = []
    rationale: list[str] = []
    suggested_tests: list[dict[str, Any]] = []
    repro_steps: list[str] = []
    analyzer_names: list[str] = []

    for report in resolved_reports:
        analyzer_names.append(report.get("dimension", "unknown"))
        findings.extend(report.get("findings", []))
        waived_findings.extend(report.get("waived_findings", []))
        suggested_tests.extend(report.get("suggested_tests", []))
        repro_steps.extend(report.get("repro_steps", []))
        rationale.extend(report.get("rationale_summary", []))
        confidence = min(confidence, report.get("confidence", 0.99))

        dimension = report["dimension"]
        verdict = report["verdict"]

        if dimension in blocking_checks and verdict == "BLOCK":
            final_verdict = "BLOCK"
        elif final_verdict != "BLOCK" and verdict == "ESCALATE":
            final_verdict = "ESCALATE"
        elif (
            final_verdict == "APPROVE"
            and dimension in advisory_checks
            and verdict in {"WARN", "ESCALATE"}
        ):
            final_verdict = "ESCALATE" if verdict == "ESCALATE" else "APPROVE"

        if final_verdict != "BLOCK" and _severity_rank(verdict) > _severity_rank(final_verdict):
            if verdict in {"APPROVE", "WARN"}:
                continue
            final_verdict = verdict

    if not rationale:
        rationale = ["No review findings were produced"]

    if final_verdict == "WARN":
        final_verdict = "APPROVE"

    risk = _derive_risk(resolved_reports)
    generated_at = datetime.now(tz=UTC).isoformat()

    return {
        "proposal_id": proposal_id,
        "final_verdict": final_verdict,
        "risk": risk,
        "confidence": confidence,
        "findings": findings,
        "waived_findings": waived_findings,
        "rationale_summary": rationale,
        "suggested_tests": suggested_tests,
        "repro_steps": repro_steps,
        "metrics": {
            "reports_evaluated": len(resolved_reports),
            "active_findings": len(findings),
            "waived_findings": len(waived_findings),
        },
        "trace": {
            "inputs": {
                "proposal_id": proposal_id,
                "report_files": source_report_files or [],
            },
            "analyzers": analyzer_names,
            "timestamps": {
                "generated_at": generated_at,
            },
        },
        "generated_at": generated_at,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--proposal", required=False)
    args = parser.parse_args()

    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    reports = [load_json_report(path) for path in args.reports]
    valid_reports = [report for report in reports if report is not None]

    proposal_id = "unknown_proposal"
    if args.proposal:
        proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
        proposal_id = proposal["id"]

    decision = aggregate_reports(
        valid_reports,
        policy,
        proposal_id=proposal_id,
        source_report_files=args.reports,
    )
    Path(args.output).write_text(json.dumps(decision, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
