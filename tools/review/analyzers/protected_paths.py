from __future__ import annotations

import argparse
import json
from fnmatch import fnmatch
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport


def run(policy_path: Path, proposal_path: Path) -> ReviewReport:
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    protected = policy["protected_paths"]["auto_escalate_on_change"]

    for changed in proposal["changed_files"]:
        if any(fnmatch(changed, pattern) for pattern in protected):
            findings.append(
                Finding(
                    file=changed,
                    line=1,
                    severity="high",
                    rule_id="PROTECTED-001",
                    finding="Protected path change requires escalation",
                )
            )

    verdict = "ESCALATE" if findings else "APPROVE"
    rationale = (
        ["Protected path changes detected"] if findings else ["No protected path changes detected"]
    )

    return ReviewReport(
        dimension="protected_paths",
        verdict=verdict,
        confidence=0.95,
        findings=findings,
        rationale_summary=rationale,
        repro_steps=(
            ["Open the changed protected file and confirm CODEOWNERS approval is present"]
            if findings
            else []
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(Path(args.policy), Path(args.context))
    report.write(args.output)


if __name__ == "__main__":
    main()
