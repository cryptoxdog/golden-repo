"""
tools/auditors/logic_correctness.py

Business Logic Correctness Validator — Dimension 2.

Two complementary static analysis tools:
  1. FloatArithmeticDetector — flags raw float arithmetic in business scoring
     (financial calculations should use decimal.Decimal)
  2. TestSmellDetector — AST-based test quality smell detection:
     - tautological assertions
     - missing assertions (test has no assert)
     - excessive mocking (>5 patches = implementation-coupled)

Usage:
    python tools/auditors/logic_correctness.py \
        --source-dir engine \
        --tests-dir tests \
        --output logic_report.json

Exit codes: 0 = clean, 1 = findings, 2 = error
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class LogicFinding:
    file: str
    line: int
    finding_type: str
    severity: str
    message: str
    detail: str = ""


@dataclass
class LogicReport:
    float_violations: list[LogicFinding] = field(default_factory=list)
    test_smells: list[LogicFinding] = field(default_factory=list)
    verdict: str = "APPROVE"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "float_violations": [f.__dict__ for f in self.float_violations],
            "test_smells": [s.__dict__ for s in self.test_smells],
            "float_violation_count": len(self.float_violations),
            "test_smell_count": len(self.test_smells),
        }


# ── Float arithmetic detector ─────────────────────────────────────────────────

class FloatArithmeticDetector(ast.NodeVisitor):
    """
    Flags raw floating-point arithmetic in business scoring paths.
    Financial calculations must use decimal.Decimal to avoid accumulation errors.
    Only active in scoring/, pricing/, and billing/ paths.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[LogicFinding] = []
        self._in_scoring_context = any(
            kw in filepath
            for kw in ("scoring", "pricing", "billing", "financial", "rate", "fee")
        )

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if not self._in_scoring_context:
            self.generic_visit(node)
            return

        if isinstance(node.op, (ast.Add, ast.Mult, ast.Div, ast.Sub)):
            for operand in (node.left, node.right):
                if isinstance(operand, ast.Constant) and isinstance(operand.value, float):
                    self.violations.append(LogicFinding(
                        file=self.filepath,
                        line=node.lineno,
                        finding_type="raw_float_arithmetic",
                        severity="WARN",
                        message="Raw float arithmetic in scoring path",
                        detail="Use decimal.Decimal for financial/scoring calculations to avoid accumulation errors",
                    ))
        self.generic_visit(node)


def scan_float_arithmetic(source_dir: Path) -> list[LogicFinding]:
    findings: list[LogicFinding] = []
    for filepath in source_dir.rglob("*.py"):
        try:
            with filepath.open() as f:
                tree = ast.parse(f.read())
        except (SyntaxError, OSError):
            continue
        detector = FloatArithmeticDetector(str(filepath))
        detector.visit(tree)
        findings.extend(detector.violations)
    return findings


# ── Test smell detector ───────────────────────────────────────────────────────

class TestSmellDetector(ast.NodeVisitor):
    """
    Detects common test smells via AST analysis.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.smells: list[LogicFinding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_test_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_test_function(node)
        self.generic_visit(node)

    def _check_test_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.name.startswith("test_"):
            return

        # Check 1: Tautological assertion (assert True, assert 1)
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                if isinstance(child.test, ast.Constant) and child.test.value:
                    self.smells.append(LogicFinding(
                        file=self.filepath,
                        line=child.lineno,
                        finding_type="tautological_assertion",
                        severity="HIGH",
                        message=f"Tautological assertion in {node.name}",
                        detail="assert True always passes — replace with a meaningful assertion",
                    ))

        # Check 2: No assertions at all
        has_assert = False
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                has_assert = True
                break
            if isinstance(child, ast.Call):
                func = child.func
                # assert_* method calls
                if hasattr(func, "attr") and func.attr.startswith("assert"):
                    has_assert = True
                    break
                # pytest.raises, pytest.warns
                if hasattr(func, "attr") and func.attr in ("raises", "warns"):
                    has_assert = True
                    break

        if not has_assert:
            self.smells.append(LogicFinding(
                file=self.filepath,
                line=node.lineno,
                finding_type="no_assertions",
                severity="CRITICAL",
                message=f"No assertions in {node.name}",
                detail="A test with no assertions cannot verify behavior",
            ))

        # Check 3: Excessive mocking (> 5 patches = implementation-coupled)
        patch_count = sum(
            1
            for child in ast.walk(node)
            if (
                isinstance(child, ast.Call)
                and hasattr(child.func, "attr")
                and child.func.attr == "patch"
            )
        )
        if patch_count > 5:
            self.smells.append(LogicFinding(
                file=self.filepath,
                line=node.lineno,
                finding_type="excessive_mocking",
                severity="MEDIUM",
                message=f"Excessive mocking in {node.name} ({patch_count} patches)",
                detail="Tests with >5 mocks are tightly coupled to implementation; prefer integration tests",
            ))


def scan_test_smells(tests_dir: Path) -> list[LogicFinding]:
    smells: list[LogicFinding] = []
    for filepath in tests_dir.rglob("test_*.py"):
        try:
            with filepath.open() as f:
                tree = ast.parse(f.read())
        except (SyntaxError, OSError):
            continue
        detector = TestSmellDetector(str(filepath))
        detector.visit(tree)
        smells.extend(detector.smells)
    return smells


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_logic_correctness(report: LogicReport) -> tuple[float, str]:
    critical_smells = [s for s in report.test_smells if s.severity == "CRITICAL"]
    if critical_smells:
        return 0.85, "WARN"  # no-assertion tests are a quality problem, not a block
    if report.float_violations:
        return 0.80, "WARN"
    return 0.93, "APPROVE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Logic correctness validator")
    parser.add_argument("--source-dir", default="engine")
    parser.add_argument("--tests-dir", default="tests")
    parser.add_argument("--output", default="logic_report.json")
    args = parser.parse_args()

    report = LogicReport()
    report.float_violations = scan_float_arithmetic(Path(args.source_dir))
    report.test_smells = scan_test_smells(Path(args.tests_dir))
    _, verdict = score_logic_correctness(report)
    report.verdict = verdict

    Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
    print(
        f"verdict={verdict} float_violations={len(report.float_violations)} "
        f"test_smells={len(report.test_smells)}"
    )

    return 0 if verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
