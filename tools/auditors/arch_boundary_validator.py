"""
tools/auditors/arch_boundary_validator.py

Architectural Boundary Validator — Dimension 1.

Validates that all changed files respect the layer DAG defined in architecture.yaml.
Produces a structured report used by both CI (deterministic block) and LLM (contextual
reasoning for novel patterns).

Usage:
    python tools/auditors/arch_boundary_validator.py \
        --changed-files changed_files.txt \
        --arch-yaml architecture.yaml \
        --output arch_report.json

Exit codes: 0 = clean, 1 = violations, 2 = error
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Violation:
    file: str
    line: int
    imported_module: str
    violation_type: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW


@dataclass
class ArchBoundaryReport:
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    novel_patterns: list[str] = field(default_factory=list)
    verdict: str = "APPROVE"  # APPROVE | WARN | BLOCK | ESCALATE

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "violations": [v.__dict__ for v in self.violations],
            "warnings": [w.__dict__ for w in self.warnings],
            "novel_patterns": self.novel_patterns,
            "is_clean": self.is_clean,
        }


# ── Architecture loader ────────────────────────────────────────────────────────

def load_architecture(arch_yaml_path: Path) -> dict:
    with arch_yaml_path.open() as f:
        return yaml.safe_load(f)


# ── Layer classification ───────────────────────────────────────────────────────

def classify_module(filepath: str, arch: dict) -> str | None:
    """Return layer name for a file path, or None if unclassified."""
    for layer_name, layer_config in arch["layers"].items():
        pattern = layer_config.get("path_pattern", "")
        regex = pattern.replace("**", ".*").replace("*", "[^/]*")
        if re.match(regex, filepath):
            return layer_name
    return None


# ── Import extraction ─────────────────────────────────────────────────────────

def extract_imports(filepath: Path) -> list[tuple[str, int]]:
    """Return (module_path, line_number) pairs for all imports."""
    try:
        with filepath.open() as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return []

    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))
    return imports


# ── Violation detection ───────────────────────────────────────────────────────

def validate_imports(
    filepath: str,
    imports: list[tuple[str, int]],
    layer: str,
    arch: dict,
) -> list[Violation]:
    violations: list[Violation] = []
    layer_config = arch["layers"][layer]
    forbidden: list[str] = layer_config.get("forbidden_imports", [])

    for module, lineno in imports:
        for forbidden_prefix in forbidden:
            fp = forbidden_prefix.replace(".", "/")
            mp = module.replace(".", "/")
            if mp == fp or mp.startswith(fp + "/"):
                violations.append(Violation(
                    file=filepath,
                    line=lineno,
                    imported_module=module,
                    violation_type=f"{layer}_imports_{forbidden_prefix}",
                    severity="CRITICAL",
                ))
    return violations


def validate_handler_signatures(filepath: Path) -> list[Violation]:
    """Verify handle_* functions conform to required signature."""
    violations: list[Violation] = []
    if "handler" not in str(filepath):
        return violations
    try:
        with filepath.open() as f:
            tree = ast.parse(f.read())
    except (SyntaxError, OSError):
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("handle_"):
            args = [a.arg for a in node.args.args]
            if args != ["tenant", "payload"]:
                violations.append(Violation(
                    file=str(filepath),
                    line=node.lineno,
                    imported_module="",
                    violation_type="invalid_handler_signature",
                    severity="HIGH",
                ))
    return violations


def scan_forbidden_patterns(filepath: Path, arch: dict) -> list[Violation]:
    """Scan source lines for handler_conventions.forbidden_patterns."""
    violations: list[Violation] = []
    forbidden = arch.get("handler_conventions", {}).get("forbidden_patterns", [])
    if not forbidden:
        return violations
    try:
        lines = filepath.read_text().splitlines()
    except OSError:
        return violations

    for i, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        for pattern in forbidden:
            if pattern in line:
                violations.append(Violation(
                    file=str(filepath),
                    line=i,
                    imported_module=pattern,
                    violation_type="forbidden_pattern",
                    severity="HIGH",
                ))
    return violations


def check_arch_exceptions(filepath: Path, violations: list[Violation]) -> list[Violation]:
    """Remove violations that have an # arch-exception: <reason> annotation on the same line."""
    try:
        lines = filepath.read_text().splitlines()
    except OSError:
        return violations

    surviving: list[Violation] = []
    for v in violations:
        if 0 < v.line <= len(lines):
            if "arch-exception:" in lines[v.line - 1]:
                continue  # annotated exception — suppressed
        surviving.append(v)
    return surviving


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_architectural_fit(report: ArchBoundaryReport) -> tuple[float, str]:
    """Returns (confidence_score 0.0-1.0, verdict)."""
    critical = [v for v in report.violations if v.severity == "CRITICAL"]
    high = [v for v in report.violations if v.severity == "HIGH"]

    if critical:
        return 0.99, "BLOCK"
    if high:
        return 0.90, "WARN"
    if report.novel_patterns:
        return 0.40, "ESCALATE"  # novel pattern → needs LLM + possible human
    return 0.97, "APPROVE"


# ── Main runner ───────────────────────────────────────────────────────────────

def run_arch_validation(
    changed_files: list[str],
    repo_root: Path,
    arch_yaml_path: Path,
) -> ArchBoundaryReport:
    arch = load_architecture(arch_yaml_path)
    report = ArchBoundaryReport()

    for file_str in changed_files:
        if not file_str.endswith(".py"):
            continue
        filepath = repo_root / file_str
        if not filepath.exists():
            continue

        layer = classify_module(file_str, arch)

        if layer is None:
            novel_policy = arch.get("novel_pattern_policy", {}).get(
                "unclassified_files_default", "ESCALATE"
            )
            if novel_policy != "IGNORE":
                report.novel_patterns.append(file_str)
            continue

        imports = extract_imports(filepath)
        raw_violations = validate_imports(file_str, imports, layer, arch)
        raw_violations += validate_handler_signatures(filepath)
        raw_violations += scan_forbidden_patterns(filepath, arch)

        # Strip arch-exception annotated violations
        clean_violations = check_arch_exceptions(filepath, raw_violations)
        report.violations.extend(clean_violations)

    confidence, verdict = score_architectural_fit(report)
    report.verdict = verdict
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Architectural boundary validator")
    parser.add_argument("--changed-files", required=True, help="File with one path per line")
    parser.add_argument("--arch-yaml", default="architecture.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="arch_report.json")
    args = parser.parse_args()

    changed = Path(args.changed_files).read_text().splitlines()
    changed = [f.strip() for f in changed if f.strip()]

    report = run_arch_validation(
        changed_files=changed,
        repo_root=Path(args.repo_root),
        arch_yaml_path=Path(args.arch_yaml),
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report.to_dict(), indent=2))
    print(f"verdict={report.verdict} violations={len(report.violations)} novel={len(report.novel_patterns)}")

    return 0 if report.verdict == "APPROVE" else 1


if __name__ == "__main__":
    sys.exit(main())
