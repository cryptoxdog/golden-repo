from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport


def classify_layer(path: str, architecture: dict) -> str | None:
    for layer_name, layer in architecture["layers"].items():
        for pattern in layer["path_patterns"]:
            if Path(path).match(pattern):
                return layer_name
    return None


def extract_imports(source: str) -> list[tuple[str, int]]:
    tree = ast.parse(source)
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def validate_handler_contract(path: Path, architecture: dict) -> list[Finding]:
    findings: list[Finding] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    has_register_all = False
    pattern = re.compile(architecture["handler_contract"]["allowed_signature_regex"])

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_all":
            has_register_all = True
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("handle_"):
            line_text = source.splitlines()[node.lineno - 1].strip()
            if not pattern.match(line_text):
                findings.append(
                    Finding(
                        file=str(path),
                        line=node.lineno,
                        severity="critical",
                        rule_id="ARCH-HANDLER-001",
                        finding="Handler signature does not match architecture contract",
                    )
                )
    if not has_register_all:
        findings.append(
            Finding(
                file=str(path),
                line=1,
                severity="critical",
                rule_id="ARCH-HANDLER-002",
                finding="engine/handlers.py must define register_all",
            )
        )
    return findings


def run(repo_root: Path, architecture_path: Path, proposal_path: Path) -> ReviewReport:
    architecture = yaml.safe_load(architecture_path.read_text(encoding="utf-8"))
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []

    for changed in proposal["changed_files"]:
        if not changed.endswith(".py"):
            continue
        file_path = repo_root / changed
        if not file_path.exists():
            continue
        layer_name = classify_layer(changed, architecture)
        if layer_name is None:
            continue
        layer = architecture["layers"][layer_name]
        source = file_path.read_text(encoding="utf-8")

        for imported, line_no in extract_imports(source):
            if any(imported.startswith(prefix) for prefix in layer["forbidden_import_prefixes"]):
                findings.append(
                    Finding(
                        file=changed,
                        line=line_no,
                        severity="critical",
                        rule_id="ARCH-IMPORT-001",
                        finding=f"{layer_name} may not import '{imported}'",
                    )
                )

        if changed == architecture["handler_contract"]["file"]:
            findings.extend(validate_handler_contract(file_path, architecture))

    verdict = "BLOCK" if findings else "APPROVE"
    rationale = (
        ["Detected forbidden cross-layer imports or handler contract violations"]
        if findings
        else ["No architectural boundary violations detected"]
    )

    return ReviewReport(
        dimension="architecture_boundary",
        verdict=verdict,
        confidence=0.99,
        findings=findings,
        rationale_summary=rationale,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(Path(args.repo_root), Path(args.architecture), Path(args.context))
    report.write(args.output)


if __name__ == "__main__":
    main()
