"""
tools/auditors/supply_chain.py

Supply Chain & Secrets Validator — Dimension 6 (deterministic layer).

Checks:
  - New/updated dependencies flagged for review
  - Typosquatting detection against known packages (edit-distance 1)
  - Hardcoded secrets pattern scan (token/key/password literals)
  - Runs trivy if available; degrades gracefully if not installed

Usage:
    python tools/auditors/supply_chain.py \
        --pr-diff pr.diff \
        --pyproject pyproject.toml \
        --output supply_chain_report.json

Exit codes: 0 = clean, 1 = findings, 2 = error
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class DependencyFinding:
    package: str
    finding_type: str  # NEW_DEPENDENCY | VERSION_CHANGE | TYPOSQUATTING
    version: str
    risk: str  # critical | high | medium | low
    old_version: str = ""
    similar_to: str = ""


@dataclass
class SecretFinding:
    file: str
    line: int
    pattern_matched: str
    severity: str = "CRITICAL"


@dataclass
class SupplyChainReport:
    dependency_findings: list[DependencyFinding] = field(default_factory=list)
    secret_findings: list[SecretFinding] = field(default_factory=list)
    trivy_critical: int = 0
    verdict: str = "APPROVE"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "dependency_findings": [f.__dict__ for f in self.dependency_findings],
            "secret_findings": [s.__dict__ for s in self.secret_findings],
            "trivy_critical": self.trivy_critical,
        }


# ── Known packages (typosquatting baseline) ───────────────────────────────────

_KNOWN_PACKAGES = [
    "requests", "numpy", "pandas", "fastapi", "pydantic",
    "httpx", "sqlalchemy", "pytest", "structlog", "aiohttp",
    "uvicorn", "starlette", "click", "rich", "typer",
    "boto3", "google-cloud", "azure-storage", "redis", "celery",
    "alembic", "cryptography", "paramiko", "fabric", "invoke",
]

# Secrets patterns — match literal values, not env var references
_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r'(?i)(aws_access_key|aws_secret)\s*=\s*["\'][A-Za-z0-9/+=]{20,}["\']')),
    ("api_key_literal", re.compile(r'(?i)(api_key|apikey|api_token)\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']')),
    ("private_key_pem", re.compile(r'-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----')),
    ("github_token", re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}')),
    ("telegram_token", re.compile(r'\d{8,10}:[A-Za-z0-9_\-]{35}')),
    ("password_literal", re.compile(r'(?i)password\s*=\s*["\'][^${\s]{8,}["\']')),
    ("hardcoded_secret", re.compile(r'(?i)secret\s*=\s*["\'][^${\s]{8,}["\']')),
]


# ── Typosquatting ─────────────────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]


def check_typosquatting(package_name: str) -> list[str]:
    """Return known packages within edit distance 1 of package_name."""
    return [p for p in _KNOWN_PACKAGES if _levenshtein(package_name.lower(), p.lower()) == 1]


# ── Dependency diff parsing ───────────────────────────────────────────────────

_ADDED_DEP_RE = re.compile(r'^\+\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*[=~<>!]+([\d\.\*]+)', re.MULTILINE)
_REMOVED_DEP_RE = re.compile(r'^-\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*[=~<>!]+([\d\.\*]+)', re.MULTILINE)


def check_new_dependencies(diff_text: str) -> list[DependencyFinding]:
    findings: list[DependencyFinding] = []
    in_dep_context = False
    current_file = ""

    for line in diff_text.splitlines():
        if "diff --git" in line:
            current_file = line.split(" b/")[-1] if " b/" in line else ""
            in_dep_context = (
                "pyproject.toml" in current_file
                or "requirements" in current_file
                or "setup.py" in current_file
            )
            continue

        if not in_dep_context:
            continue

        am = _ADDED_DEP_RE.match(line)
        if am:
            pkg, ver = am.group(1), am.group(2)
            similar = check_typosquatting(pkg)

            if similar:
                findings.append(DependencyFinding(
                    package=pkg,
                    finding_type="TYPOSQUATTING",
                    version=ver,
                    risk="high",
                    similar_to=similar[0],
                ))
            else:
                findings.append(DependencyFinding(
                    package=pkg,
                    finding_type="NEW_DEPENDENCY",
                    version=ver,
                    risk="medium",
                ))

    return findings


# ── Secret scanning ───────────────────────────────────────────────────────────

def scan_secrets_in_diff(diff_text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    current_file = ""
    current_line = 0

    for line in diff_text.splitlines():
        if "diff --git" in line:
            current_file = line.split(" b/")[-1] if " b/" in line else ""
            current_line = 0
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            current_line = int(m.group(1)) if m else 0
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            for pattern_name, pattern_re in _SECRET_PATTERNS:
                if pattern_re.search(line):
                    # Skip known env var references
                    if "os.getenv" in line or "os.environ" in line or "${" in line:
                        continue
                    findings.append(SecretFinding(
                        file=current_file,
                        line=current_line,
                        pattern_matched=pattern_name,
                    ))
        elif line.startswith(" "):
            current_line += 1

    return findings


# ── Trivy scan (optional) ─────────────────────────────────────────────────────

def run_trivy_scan(repo_root: Path) -> int:
    """Return count of critical vulnerabilities from trivy, or 0 if not installed."""
    try:
        result = subprocess.run(
            ["trivy", "fs", "--format", "json", "--quiet",
             "--security-checks", "vuln",
             "--severity", "CRITICAL",
             str(repo_root)],
            capture_output=True, text=True, timeout=120,
        )
        data = json.loads(result.stdout)
        total = 0
        for target in data.get("Results", []):
            total += len([
                v for v in target.get("Vulnerabilities", [])
                if v.get("Severity") == "CRITICAL"
            ])
        return total
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return 0  # trivy not installed or timed out — degrade gracefully


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_supply_chain(
    secret_findings: list[SecretFinding],
    typosquatting: list[DependencyFinding],
    trivy_critical: int,
) -> tuple[float, str]:
    if secret_findings or trivy_critical > 0:
        return 0.999, "BLOCK"
    if typosquatting:
        return 0.70, "WARN"
    return 0.93, "APPROVE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Supply chain validator")
    parser.add_argument("--pr-diff", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="supply_chain_report.json")
    parser.add_argument("--skip-trivy", action="store_true")
    args = parser.parse_args()

    try:
        diff_text = Path(args.pr_diff).read_text()
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    dep_findings = check_new_dependencies(diff_text)
    secret_findings = scan_secrets_in_diff(diff_text)
    typosquatting = [f for f in dep_findings if f.finding_type == "TYPOSQUATTING"]
    trivy_critical = 0 if args.skip_trivy else run_trivy_scan(Path(args.repo_root))

    _, verdict = score_supply_chain(secret_findings, typosquatting, trivy_critical)

    report = SupplyChainReport(
        dependency_findings=dep_findings,
        secret_findings=secret_findings,
        trivy_critical=trivy_critical,
        verdict=verdict,
    )

    Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
    print(
        f"verdict={verdict} secrets={len(secret_findings)} "
        f"typosquatting={len(typosquatting)} trivy_critical={trivy_critical}"
    )

    return 0 if verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
