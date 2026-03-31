from __future__ import annotations

import argparse
import ast
import json
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


def validate_handler_contract(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    has_register_all = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_all":
            has_register_all = True
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("handle_"):
            arg_names = [arg.arg for arg in node.args.args]
            if arg_names != ["tenant", "payload"]:
                findings.append(
                    Finding(
                        file=str(path).replace("\\", "/"),
                        line=node.lineno,
                        severity="critical",
                        rule_id="ARCH-HANDLER-001",
                        finding="Handler signature must be (tenant, payload)",
                    )
                )
    if not has_register_all:
        findings.append(
            Finding(
                file=str(path).replace("\\", "/"),
                line=1,
                severity="critical",
                rule_id="ARCH-HANDLER-002",
                finding="engine/handlers.py must define register_all",
            )
        )
    if ".model_validate(payload)" not in source:
        findings.append(
            Finding(
                file=str(path).replace("\\", "/"),
                line=1,
                severity="high",
                rule_id="ARCH-HANDLER-003",
                finding="Handler file should validate payloads with model_validate(payload)",
            )
        )
    return findings


def run(repo_root: Path, architecture_path: Path, context_path: Path) -> ReviewReport:
    architecture = yaml.safe_load(architecture_path.read_text(encoding="utf-8"))
    context = json.loads(context_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []

    for changed in context["changed_files"]:
        if not changed.endswith(".py"):
            continue
        layer_name = classify_layer(changed, architecture)
        if layer_name is None:
            continue
        path = repo_root / changed
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        imports = extract_imports(source)
        forbidden = architecture["layers"][layer_name]["forbidden_import_prefixes"]

        for imported_module, lineno in imports:
            if any(
                imported_module == prefix or imported_module.startswith(f"{prefix}.")
                for prefix in forbidden
            ):
                findings.append(
                    Finding(
                        file=changed,
                        line=lineno,
                        severity="critical",
                        rule_id="ARCH-IMPORT-001",
                        finding=f"{layer_name} may not import {imported_module}",
                    )
                )

        if changed == architecture["handler_contract"]["file"]:
            findings.extend(validate_handler_contract(path))

    verdict = "BLOCK" if any(item.severity == "critical" for item in findings) else (
        "ESCALATE" if findings else "APPROVE"
    )
    rationale = ["Architecture boundary violations detected"] if findings else [
        "No architecture boundary violations detected"
    ]

    return ReviewReport(
        dimension="architecture_boundary",
        verdict=verdict,
        confidence=0.99 if verdict == "BLOCK" else 0.95,
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
