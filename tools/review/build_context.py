from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def build_context(base_ref: str, head_ref: str) -> dict:
    changed_files = [
        line.strip()
        for line in run_git("diff", "--name-only", f"{base_ref}...{head_ref}").splitlines()
        if line.strip()
    ]
    diff = run_git("diff", "--unified=3", f"{base_ref}...{head_ref}")
    changed_lines = sum(
        1 for line in diff.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    )
    protected_hits = [
        item for item in changed_files
        if item.startswith(".github/workflows/") or item.startswith("tools/review/policy/")
    ]
    return {
        "base_ref": base_ref,
        "head_ref": head_ref,
        "changed_files": changed_files,
        "changed_lines": changed_lines,
        "diff": diff,
        "spec_changed": "spec.yaml" in changed_files or any(
            item.startswith("domains/") and item.endswith("spec.yaml")
            for item in changed_files
        ),
        "workflow_changed": any(item.startswith(".github/workflows/") for item in changed_files),
        "policy_changed": any(item.startswith("tools/review/policy/") for item in changed_files),
        "protected_path_hits": protected_hits,
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    context = build_context(args.base_ref, args.head_ref)
    Path(args.output).write_text(json.dumps(context, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
