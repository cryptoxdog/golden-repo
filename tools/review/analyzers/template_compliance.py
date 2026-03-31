from __future__ import annotations

import argparse
import ast
import json
from fnmatch import fnmatch
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport


def _defined_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def run(repo_root: Path, manifest_path: Path, proposal_path: Path) -> ReviewReport:  # noqa: C901
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []

    for entry in manifest["required_files"]:
        path = repo_root / entry["path"]
        if not path.is_file():
            findings.append(
                Finding(
                    file=entry["path"],
                    line=1,
                    severity="critical",
                    rule_id="TEMPLATE-001",
                    finding="Required file is missing",
                )
            )

    for entry in manifest.get("required_directories", []):
        path = repo_root / entry["path"]
        if not path.is_dir():
            findings.append(
                Finding(
                    file=entry["path"],
                    line=1,
                    severity="critical",
                    rule_id="TEMPLATE-002",
                    finding="Required directory is missing",
                )
            )

    changed_files = proposal["changed_files"]
    for protected in manifest.get("protected_files", []):
        if protected["path"] in changed_files:
            findings.append(
                Finding(
                    file=protected["path"],
                    line=1,
                    severity="critical",
                    rule_id="TEMPLATE-003",
                    finding="Protected template file was modified",
                )
            )

    for rule in manifest.get("required_symbols", []):
        file_path = repo_root / rule["file"]
        if not file_path.exists():
            continue
        names = _defined_names(file_path.read_text(encoding="utf-8"))
        for symbol in rule["symbols"]:
            if symbol not in names:
                findings.append(
                    Finding(
                        file=rule["file"],
                        line=1,
                        severity="critical",
                        rule_id="TEMPLATE-004",
                        finding=f"Required symbol '{symbol}' is missing",
                    )
                )

    version_file = repo_root / ".l9-template-version"
    if not version_file.exists():
        findings.append(
            Finding(
                file=".l9-template-version",
                line=1,
                severity="critical",
                rule_id="TEMPLATE-005",
                finding="Template version file is missing",
            )
        )
    elif not version_file.read_text(encoding="utf-8").strip():
        findings.append(
            Finding(
                file=".l9-template-version",
                line=1,
                severity="critical",
                rule_id="TEMPLATE-006",
                finding="Template version file must not be empty",
            )
        )

    for pattern in manifest.get("prohibited_paths", []):
        for changed in changed_files:
            if fnmatch(changed, pattern):
                findings.append(
                    Finding(
                        file=changed,
                        line=1,
                        severity="critical",
                        rule_id="TEMPLATE-007",
                        finding="Change touches prohibited template path",
                    )
                )

    verdict = "BLOCK" if findings else "APPROVE"
    rationale = (
        ["Repository deviates from template manifest"]
        if findings
        else ["All required files, directories, and symbols are present"]
    )

    return ReviewReport(
        dimension="template_compliance",
        verdict=verdict,
        confidence=0.99,
        findings=findings,
        rationale_summary=rationale,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(Path(args.repo_root), Path(args.manifest), Path(args.context))
    report.write(args.output)


if __name__ == "__main__":
    main()
