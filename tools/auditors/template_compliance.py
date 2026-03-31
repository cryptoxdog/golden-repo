"""
tools/auditors/template_compliance.py

Golden Template Compliance Validator — Dimension 5.

Validates repo structural conformance against the golden template manifest:
  - Required files and directories exist
  - Required symbols are defined in required files
  - Prohibited paths are absent from changed files
  - Protected files have not been modified
  - .l9-template-version matches manifest major version

Usage:
    python tools/auditors/template_compliance.py \
        --changed-files changed_files.txt \
        --manifest tools/review/policy/template_manifest.yaml \
        --repo-root . \
        --output template_report.json

Exit codes: 0 = APPROVE, 1 = BLOCK/WARN, 2 = error
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
class ComplianceResult:
    missing_files: list[str] = field(default_factory=list)
    missing_directories: list[str] = field(default_factory=list)
    prohibited_paths: list[str] = field(default_factory=list)
    missing_symbols: list[dict] = field(default_factory=list)
    modified_protected_files: list[str] = field(default_factory=list)
    template_version: str = ""
    node_template_version: str = ""
    version_compatible: bool = True
    verdict: str = "APPROVE"

    @property
    def is_compliant(self) -> bool:
        return (
            not self.missing_files
            and not self.missing_directories
            and not self.prohibited_paths
            and not self.missing_symbols
            and not self.modified_protected_files
            and self.version_compatible
        )

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "is_compliant": self.is_compliant,
            "missing_files": self.missing_files,
            "missing_directories": self.missing_directories,
            "prohibited_paths": self.prohibited_paths,
            "missing_symbols": self.missing_symbols,
            "modified_protected_files": self.modified_protected_files,
            "template_version": self.template_version,
            "node_template_version": self.node_template_version,
            "version_compatible": self.version_compatible,
        }


# ── Manifest loader ───────────────────────────────────────────────────────────

def load_manifest(manifest_path: Path) -> dict:
    with manifest_path.open() as f:
        return yaml.safe_load(f)


# ── Checks ────────────────────────────────────────────────────────────────────

def check_required_files(manifest: dict, repo_root: Path) -> list[str]:
    missing: list[str] = []
    for req in manifest.get("required_files", []):
        path = repo_root / req["path"]
        if not path.exists():
            missing.append(req["path"])
    return missing


def check_required_directories(manifest: dict, repo_root: Path) -> list[str]:
    missing: list[str] = []
    for req in manifest.get("required_directories", []):
        path = repo_root / req["path"]
        if not path.is_dir():
            missing.append(req["path"])
    return missing


def check_required_symbols(manifest: dict, repo_root: Path) -> list[dict]:
    issues: list[dict] = []
    for req in manifest.get("required_symbols", []):
        filepath = repo_root / req["file"]
        if not filepath.exists():
            continue
        try:
            with filepath.open() as f:
                tree = ast.parse(f.read())
        except (SyntaxError, OSError):
            continue

        defined_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)

        for sym in req.get("symbols", []):
            if sym not in defined_names:
                issues.append({"file": req["file"], "missing_symbol": sym})
    return issues


def check_prohibited_paths(
    manifest: dict,
    repo_root: Path,
    changed_files: list[str],
) -> list[str]:
    violations: list[str] = []
    for pattern in manifest.get("prohibited_paths", []):
        regex = pattern.replace("**", ".*").replace("*", "[^/]*")
        for changed_file in changed_files:
            if re.match(regex, changed_file):
                violations.append(changed_file)
    return violations


def check_protected_files_unmodified(
    manifest: dict,
    changed_files: list[str],
) -> list[str]:
    protected = [
        req["path"]
        for req in manifest.get("protected_files", [])
    ]
    return [f for f in changed_files if f in protected]


def check_template_version(manifest: dict, repo_root: Path) -> tuple[str, bool]:
    """Read .l9-template-version and check semver major compatibility."""
    version_file = repo_root / ".l9-template-version"
    if not version_file.exists():
        return "unknown", False

    node_version = version_file.read_text().strip()
    template_version = manifest.get("version", "0.0.0")

    node_major = node_version.split(".")[0] if node_version != "unknown" else "0"
    template_major = template_version.split(".")[0]

    return node_version, node_major == template_major


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_template_compliance(result: ComplianceResult) -> tuple[float, str]:
    if result.modified_protected_files:
        return 0.999, "BLOCK"
    if not result.version_compatible:
        return 0.990, "BLOCK"
    if result.missing_files or result.missing_symbols:
        return 0.990, "BLOCK"
    if result.prohibited_paths:
        return 0.990, "BLOCK"
    if result.missing_directories:
        return 0.990, "BLOCK"
    return 0.990, "APPROVE"


# ── Runner ────────────────────────────────────────────────────────────────────

def run_template_compliance(
    repo_root: Path,
    manifest_path: Path,
    changed_files: list[str],
) -> ComplianceResult:
    manifest = load_manifest(manifest_path)
    result = ComplianceResult()
    result.template_version = manifest.get("version", "")

    result.missing_files = check_required_files(manifest, repo_root)
    result.missing_directories = check_required_directories(manifest, repo_root)
    result.missing_symbols = check_required_symbols(manifest, repo_root)
    result.prohibited_paths = check_prohibited_paths(manifest, repo_root, changed_files)
    result.modified_protected_files = check_protected_files_unmodified(manifest, changed_files)

    node_ver, compat = check_template_version(manifest, repo_root)
    result.node_template_version = node_ver
    result.version_compatible = compat

    _, verdict = score_template_compliance(result)
    result.verdict = verdict
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Template compliance validator")
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--manifest", default="tools/review/policy/template_manifest.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="template_report.json")
    args = parser.parse_args()

    changed = Path(args.changed_files).read_text().splitlines()
    changed = [f.strip() for f in changed if f.strip()]

    result = run_template_compliance(
        repo_root=Path(args.repo_root),
        manifest_path=Path(args.manifest),
        changed_files=changed,
    )

    Path(args.output).write_text(json.dumps(result.to_dict(), indent=2))
    print(
        f"verdict={result.verdict} compliant={result.is_compliant} "
        f"missing_files={result.missing_files} "
        f"protected_modified={result.modified_protected_files}"
    )

    return 0 if result.verdict == "APPROVE" else 1


if __name__ == "__main__":
    sys.exit(main())
