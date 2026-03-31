from __future__ import annotations

import argparse
import ast
from fnmatch import fnmatch
import json
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


def run(repo_root: Path, manifest_path: Path, context_path: Path) -> ReviewReport:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    context = json.loads(context_path.read_text(encoding="utf-8"))
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

    changed_files = context["changed_files"]
    protected_paths = {entry["path"] for entry in manifest.get("protected_files", [])}
    for changed in changed_files:
        if changed in protected_paths:
            findings.append(
                Finding(
                    file=changed,
                    line=1,
                    severity="critical",
                    rule_id="TEMPLATE-003",
                    finding="Protected template file was modified",
                )
            )

    for item in manifest.get("required_symbols", []):
        path = repo_root / item["file"]
        if not path.exists():
            continue
        names = _defined_names(path.read_text(encoding="utf-8"))
        for symbol in item["symbols"]:
            if symbol not in names:
                findings.append(
                    Finding(
                        file=item["file"],
                        line=1,
                        severity="critical",
                        rule_id="TEMPLATE-004",
                        finding=f"Required symbol {symbol!r} is missing",
                    )
                )

    for changed in changed_files:
        for pattern in manifest.get("prohibited_paths", []):
            if fnmatch(changed, pattern):
                findings.append(
                    Finding(
                        file=changed,
                        line=1,
                        severity="critical",
                        rule_id="TEMPLATE-005",
                        finding=f"Changed file matches prohibited path pattern {pattern!r}",
                    )
                )

    version_file = repo_root / ".l9-template-version"
    if not version_file.exists():
        findings.append(
            Finding(
                file=".l9-template-version",
                line=1,
                severity="critical",
                rule_id="TEMPLATE-006",
                finding="Template version file is missing",
            )
        )

    verdict = "BLOCK" if findings else "APPROVE"
    rationale = (
        ["Template compliance failures detected"]
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
