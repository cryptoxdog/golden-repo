from __future__ import annotations

import argparse
from pathlib import Path

import jsonschema
import yaml

from tools.review.report import Finding, ReviewReport


def run(policy_path: Path) -> ReviewReport:
    repo_root = policy_path.parents[3]
    findings: list[Finding] = []

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    architecture_path = repo_root / "tools/review/policy/architecture.yaml"
    manifest_path = repo_root / "tools/review/policy/template_manifest.yaml"
    schema_path = repo_root / "tools/review/policy/spec_schema.json"
    spec_path = repo_root / "spec.yaml"

    architecture = yaml.safe_load(architecture_path.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    spec_schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    if "blocking_checks" not in policy:
        findings.append(Finding(file=str(policy_path.relative_to(repo_root)), line=1, severity="critical", rule_id="YAML-001", finding="review_policy.yaml must define blocking_checks"))
    if "layers" not in architecture:
        findings.append(Finding(file=str(architecture_path.relative_to(repo_root)), line=1, severity="critical", rule_id="YAML-002", finding="architecture.yaml must define layers"))
    if "required_files" not in manifest:
        findings.append(Finding(file=str(manifest_path.relative_to(repo_root)), line=1, severity="critical", rule_id="YAML-003", finding="template_manifest.yaml must define required_files"))

    validator = jsonschema.Draft7Validator(spec_schema)
    for error in validator.iter_errors(spec):
        findings.append(
            Finding(
                file=str(spec_path.relative_to(repo_root)),
                line=1,
                severity="critical",
                rule_id="YAML-004",
                finding=error.message,
            )
        )

    verdict = "BLOCK" if findings else "APPROVE"
    rationale = ["YAML validation completed"] if not findings else ["YAML validation failures detected"]

    return ReviewReport(
        dimension="yaml_validation",
        verdict=verdict,
        confidence=0.99,
        findings=findings,
        rationale_summary=rationale,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(Path(args.policy))
    report.write(args.output)


if __name__ == "__main__":
    main()
