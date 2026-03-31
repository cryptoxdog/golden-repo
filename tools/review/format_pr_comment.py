from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_comment(report: dict) -> str:
    verdict = report.get("final_verdict", report.get("verdict", "APPROVE"))
    lines = [f"## AI Review Verdict: {verdict}", ""]
    for item in report.get("rationale_summary", []):
        lines.append(f"- {item}")
    findings = report.get("findings", [])
    if findings:
        lines.extend(["", "### Findings"])
        for finding in findings[:20]:
            lines.append(
                f"- `{finding['rule_id']}` {finding['file']}:{finding['line']} — {finding['finding']}"
            )
    waived = report.get("waived_findings", [])
    if waived:
        lines.extend(["", "### Waived Findings"])
        for finding in waived[:20]:
            reason = finding.get("waiver_reason", "waived")
            lines.append(
                f"- `{finding['rule_id']}` {finding['file']}:{finding['line']} — {finding['finding']} ({reason})"
            )
    suggested_tests = report.get("suggested_tests", [])
    if suggested_tests:
        lines.extend(["", "### Suggested Tests"])
        for test in suggested_tests[:10]:
            lines.append(
                f"- `{test['file']}` → `{test['name']}`: {test['assertion']}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    comment = build_comment(report)
    Path(args.output).write_text(comment, encoding="utf-8")


if __name__ == "__main__":
    main()
