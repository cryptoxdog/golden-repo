"""
tools/auditors/performance_impact.py

Performance & Operational Impact Auditor — Dimension 8.

Static analysis for operational safety patterns:
  - N+1 query patterns (database calls inside loops)
  - asyncio.create_task without result stored (orphaned tasks)
  - HTTP calls without explicit timeout
  - Missing circuit breaker for external integrations
  - Synchronous I/O in async functions (blocking event loop)
  - Unbounded list accumulation from external data

Usage:
    python tools/auditors/performance_impact.py \
        --changed-files changed_files.txt \
        --spec spec.yaml \
        --repo-root . \
        --output perf_report.json

Exit codes: 0 = APPROVE/WARN, 1 = BLOCK, 2 = error
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class OperationalIssue:
    file: str
    line: int
    issue_type: str
    severity: str
    detail: str


@dataclass
class PerformanceReport:
    issues: list[OperationalIssue] = field(default_factory=list)
    verdict: str = "APPROVE"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "issues": [i.__dict__ for i in self.issues],
            "critical_count": len([i for i in self.issues if i.severity == "CRITICAL"]),
            "high_count": len([i for i in self.issues if i.severity == "HIGH"]),
        }


# ── AST visitor ───────────────────────────────────────────────────────────────

class OperationalPatternAuditor(ast.NodeVisitor):
    """
    Detects missing operational safety patterns.
    Focuses on async Python / FastAPI / Neo4j driver patterns.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[OperationalIssue] = []
        self._loop_depth = 0
        self._in_async_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev = self._in_async_function
        self._in_async_function = True
        self.generic_visit(node)
        self._in_async_function = prev

    def visit_For(self, node: ast.For) -> None:
        self._loop_depth += 1
        self._check_loop_for_n_plus_one(node)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def _check_loop_for_n_plus_one(self, node: ast.For) -> None:
        """Detect awaited calls inside loops — potential N+1 pattern."""
        _QUERY_KEYWORDS = ("execute_query", "execute_write", "query", "fetch",
                           "find_one", "find_all", "get_by_id", "select", "execute")
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.Await):
                call_str = ast.unparse(child)
                if any(kw in call_str.lower() for kw in _QUERY_KEYWORDS):
                    self.issues.append(OperationalIssue(
                        file=self.filepath,
                        line=node.lineno,
                        issue_type="potential_n_plus_one",
                        severity="HIGH",
                        detail=(
                            f"Possible N+1 pattern at line {node.lineno}: "
                            f"awaited DB/query call inside a loop. "
                            f"Use UNWIND batch or collect IDs first."
                        ),
                    ))
                    break  # one finding per loop, don't spam

    def visit_Call(self, node: ast.Call) -> None:
        call_str = ast.unparse(node)

        # asyncio.create_task without storing result → orphaned task
        if "asyncio.create_task" in call_str:
            # If not part of an assignment, it's orphaned
            self.issues.append(OperationalIssue(
                file=self.filepath,
                line=node.lineno,
                issue_type="orphaned_background_task",
                severity="HIGH",
                detail=(
                    "asyncio.create_task() called — verify the task handle is "
                    "stored and cancelled on shutdown to prevent task leaks."
                ),
            ))

        # HTTP calls without explicit timeout
        _HTTP_PATTERNS = ("httpx.get", "httpx.post", "httpx.request",
                          "client.get", "client.post", "client.request",
                          "session.get", "session.post")
        if any(p in call_str for p in _HTTP_PATTERNS):
            if "timeout" not in call_str:
                self.issues.append(OperationalIssue(
                    file=self.filepath,
                    line=node.lineno,
                    issue_type="http_call_no_timeout",
                    severity="CRITICAL",
                    detail=(
                        f"HTTP call at line {node.lineno} has no explicit timeout. "
                        "A slow or unresponsive downstream will block indefinitely."
                    ),
                ))

        # Synchronous blocking calls inside async functions
        _BLOCKING_PATTERNS = ("time.sleep(", "open(", "requests.get", "requests.post")
        if self._in_async_function:
            for pattern in _BLOCKING_PATTERNS:
                if pattern in call_str:
                    self.issues.append(OperationalIssue(
                        file=self.filepath,
                        line=node.lineno,
                        issue_type="blocking_call_in_async",
                        severity="HIGH",
                        detail=(
                            f"Blocking call '{pattern}' inside async function at line {node.lineno}. "
                            "This blocks the event loop — use async equivalent."
                        ),
                    ))

        self.generic_visit(node)


# ── Circuit breaker check ─────────────────────────────────────────────────────

def check_circuit_breaker_presence(
    handler_file: Path,
    spec: dict,
    action_name: str,
) -> list[OperationalIssue]:
    """Verify circuit breaker present if action integrates with external services."""
    action = next(
        (a for a in spec.get("actions", []) if isinstance(a, dict) and a.get("name") == action_name),
        None,
    )
    if not action or not action.get("integrations"):
        return []

    try:
        content = handler_file.read_text()
    except OSError:
        return []

    _CB_PATTERNS = ("CircuitBreaker", "circuit_breaker", "tenacity", "stamina", "breaker")
    if not any(p in content for p in _CB_PATTERNS):
        return [OperationalIssue(
            file=str(handler_file),
            line=0,
            issue_type="missing_circuit_breaker",
            severity="CRITICAL",
            detail=(
                f"Handler '{action_name}' integrates with external services "
                "but has no circuit breaker (tenacity, stamina, or CircuitBreaker). "
                "External failures will cascade."
            ),
        )]
    return []


# ── Assertion density ─────────────────────────────────────────────────────────

def compute_assertion_density(test_file: Path) -> float:
    """Ratio of assertions to test functions. Target: >= 3."""
    try:
        with test_file.open() as f:
            tree = ast.parse(f.read())
    except (SyntaxError, OSError):
        return 0.0

    test_count = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    )
    assert_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert))
    return assert_count / max(test_count, 1)


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_performance_impact(issues: list[OperationalIssue]) -> tuple[float, str]:
    critical = [i for i in issues if i.severity == "CRITICAL"]
    high = [i for i in issues if i.severity == "HIGH"]
    if critical:
        return 0.97, "BLOCK"
    if len(high) > 3:
        return 0.75, "WARN"
    if high:
        return 0.82, "WARN"
    return 0.90, "APPROVE"


# ── Runner ────────────────────────────────────────────────────────────────────

def run_performance_audit(
    changed_files: list[str],
    repo_root: Path,
    spec_path: Path | None = None,
) -> PerformanceReport:
    report = PerformanceReport()
    spec: dict = {}
    if spec_path and spec_path.exists():
        with spec_path.open() as f:
            spec = yaml.safe_load(f) or {}

    for file_str in changed_files:
        if not file_str.endswith(".py"):
            continue
        filepath = repo_root / file_str
        if not filepath.exists():
            continue

        try:
            with filepath.open() as f:
                tree = ast.parse(f.read())
        except (SyntaxError, OSError):
            continue

        auditor = OperationalPatternAuditor(file_str)
        auditor.visit(tree)
        report.issues.extend(auditor.issues)

        # Check circuit breakers for spec actions
        if "handler" in file_str and spec:
            for action in spec.get("actions", []):
                if isinstance(action, dict):
                    action_name = action.get("name", "")
                    report.issues.extend(
                        check_circuit_breaker_presence(filepath, spec, action_name)
                    )

    _, verdict = score_performance_impact(report.issues)
    report.verdict = verdict
    return report


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Performance/operational impact auditor")
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--spec", default="spec.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="perf_report.json")
    args = parser.parse_args()

    changed = Path(args.changed_files).read_text().splitlines()
    changed = [f.strip() for f in changed if f.strip()]

    spec_path = Path(args.spec)
    report = run_performance_audit(
        changed_files=changed,
        repo_root=Path(args.repo_root),
        spec_path=spec_path if spec_path.exists() else None,
    )

    Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
    print(
        f"verdict={report.verdict} "
        f"critical={report.to_dict()['critical_count']} "
        f"high={report.to_dict()['high_count']}"
    )
    return 0 if report.verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
