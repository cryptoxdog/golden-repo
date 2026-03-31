from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport, SuggestedTest


def run(context_path: Path, policy_path: Path) -> ReviewReport:
    context = json.loads(context_path.read_text(encoding="utf-8"))
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    suggested_tests: list[SuggestedTest] = []
    repro_steps: list[str] = []

    changed_lines = context["changed_lines"]
    if changed_lines > policy["size_limits"]["max_changed_lines_for_semantic_review"]:
        findings.append(
            Finding(
                file="*",
                line=1,
                severity="high",
                rule_id="SEM-001",
                finding="Change exceeds semantic review budget and should be split for reliable analysis",
            )
        )
        repro_steps.append("Split the PR into smaller units and rerun deterministic + semantic review.")

    if context["spec_changed"] and not any(path.startswith("tests/") for path in context["changed_files"]):
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
                name="test_spec_change_has_runtime_coverage",
                file="tests/unit/test_spec_runtime_coverage.py",
                purpose="Protect behavior implied by spec changes.",
                assertion="Assert every changed spec action has a corresponding behavior test.",
            )
        )
        repro_steps.append("Add or update tests that exercise each changed action in spec.yaml.")

    if any(path.startswith("engine/services/") for path in context["changed_files"]) and not any(path.startswith("tests/") for path in context["changed_files"]):
        findings.append(
            Finding(
                file="engine/services/",
                line=1,
                severity="medium",
                rule_id="SEM-003",
                finding="Service-layer logic changed without tests in the same PR",
            )
        )
        suggested_tests.append(
            SuggestedTest(
                name="test_service_logic_regression",
                file="tests/unit/test_action_service_regression.py",
                purpose="Lock in changed service semantics.",
                assertion="Assert old and new expected outputs for modified service behaviors.",
            )
        )

    verdict = "ESCALATE" if any(f.severity == "high" for f in findings) else ("WARN" if findings else "APPROVE")
    rationale = ["Semantic escalation conditions detected"] if findings else ["No semantic escalation conditions detected"]

    return ReviewReport(
        dimension="semantic_review",
        verdict=verdict,
        confidence=0.75 if findings else 0.90,
        findings=findings,
        rationale_summary=rationale,
        suggested_tests=suggested_tests,
        repro_steps=repro_steps,
        metrics={
            "changed_lines": changed_lines,
            "spec_changed": context["spec_changed"],
        },
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
