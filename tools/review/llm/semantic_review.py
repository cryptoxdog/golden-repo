from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport, SuggestedTest


def run(proposal_path: Path, policy_path: Path) -> ReviewReport:
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    suggested_tests: list[SuggestedTest] = []
    repro_steps: list[str] = []
    metadata = proposal.get("metadata", {})

    changed_lines = proposal["changed_lines"]
    if changed_lines > policy["size_limits"]["max_changed_lines_for_semantic_review"]:
        findings.append(
            Finding(
                file="*",
                line=1,
                severity="high",
                rule_id="SEM-001",
                finding="Change exceeds semantic review budget and should be split for reliable analysis",  # noqa: E501
            )
        )
        repro_steps.append(
            "Split the proposal into smaller units and rerun deterministic + semantic review."
        )

    if metadata.get("spec_changed") and not any(
        path.startswith("tests/") for path in proposal["changed_files"]
    ):
        findings.append(
            Finding(
                file="spec.yaml",
                line=1,
                severity="medium",
                rule_id="SEM-002",
                finding="Spec changed without accompanying test change; review behavioral coverage",
            )
        )
        suggested_tests.append(
            SuggestedTest(
                name="spec_behavior_regression",
                file="tests/unit/test_spec_loader.py",
                purpose="Ensure spec changes preserve expected action coverage and behavior",
                assertion="Updated spec actions must remain reachable through registered handlers",
            )
        )

    verdict = (
        "ESCALATE"
        if any(item.severity == "high" for item in findings)
        else ("WARN" if findings else "APPROVE")
    )
    rationale = (
        ["Semantic review detected ambiguity or coverage gaps"]
        if findings
        else ["No semantic escalation conditions detected"]
    )

    return ReviewReport(
        dimension="semantic_review",
        verdict=verdict,
        confidence=0.70 if findings else 0.85,
        findings=findings,
        rationale_summary=rationale,
        suggested_tests=suggested_tests,
        repro_steps=repro_steps,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(Path(args.context), Path(args.policy))
    report.write(args.output)


if __name__ == "__main__":
    main()
