from __future__ import annotations

import argparse
import ast
from pathlib import Path

import yaml

from tools.review.report import Finding, ReviewReport


def extract_registered_handlers(handler_path: Path) -> set[str]:
    source = handler_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    registered: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_all":
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if (
                            isinstance(target, ast.Subscript)
                            and isinstance(target.slice, ast.Constant)
                            and isinstance(target.slice.value, str)
                        ):
                            registered.add(target.slice.value)
    return registered


def extract_handler_functions(handler_path: Path) -> set[str]:
    tree = ast.parse(handler_path.read_text(encoding="utf-8"))
    return {
        node.name.removeprefix("handle_")
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("handle_")
    }


def run(repo_root: Path, spec_path: Path) -> ReviewReport:
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec_actions = {action["name"] for action in spec.get("actions", [])}
    handler_path = repo_root / "engine/handlers.py"
    registered = extract_registered_handlers(handler_path)
    functions = extract_handler_functions(handler_path)
    findings: list[Finding] = []

    for action_name in sorted(spec_actions - registered):
        findings.append(
            Finding(
                file="spec.yaml",
                line=1,
                severity="critical",
                rule_id="SPEC-COVERAGE-001",
                finding=f"Action '{action_name}' is defined in spec.yaml but not registered",
            )
        )
    for action_name in sorted(spec_actions - functions):
        findings.append(
            Finding(
                file="engine/handlers.py",
                line=1,
                severity="critical",
                rule_id="SPEC-COVERAGE-002",
                finding=f"Action '{action_name}' is defined in spec.yaml but handler function is missing",  # noqa: E501
            )
        )
    for action_name in sorted(registered - spec_actions):
        findings.append(
            Finding(
                file="engine/handlers.py",
                line=1,
                severity="high",
                rule_id="SPEC-COVERAGE-003",
                finding=f"Registered handler '{action_name}' is not defined in spec.yaml",
            )
        )

    verdict = "BLOCK" if any(item.severity == "critical" for item in findings) else "APPROVE"
    rationale = (
        ["Spec action coverage is incomplete"]
        if findings
        else ["All spec actions are implemented and registered"]
    )

    return ReviewReport(
        dimension="spec_coverage",
        verdict=verdict,
        confidence=0.98,
        findings=findings,
        rationale_summary=rationale,
        metrics={
            "spec_actions": len(spec_actions),
            "registered_handlers": len(registered),
            "coverage_ratio": len(spec_actions & registered) / max(len(spec_actions), 1),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(Path(args.repo_root), Path(args.spec))
    report.write(args.output)


if __name__ == "__main__":
    main()
