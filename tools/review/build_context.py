from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def run_git(*args: str) -> str:
    completed = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def infer_change_type(changed_files: list[str]) -> str:
    if any(path.startswith(".github/workflows/") for path in changed_files):
        return "workflow_change"
    if "spec.yaml" in changed_files or any(
        path.startswith("domains/") and path.endswith("/spec.yaml") for path in changed_files
    ):
        return "spec_change"
    if any(
        path.startswith("tools/review/policy/") or path.endswith((".yaml", ".yml", ".json"))
        for path in changed_files
    ):
        return "config_change"
    return "code_change"


def build_change_proposal(base_ref: str, head_ref: str, source: str = "git_pr") -> dict[str, Any]:
    changed_files = sorted(
        {
            line.strip()
            for line in run_git("diff", "--name-only", f"{base_ref}...{head_ref}").splitlines()
            if line.strip()
        }
    )
    diff = run_git("diff", "--unified=3", f"{base_ref}...{head_ref}")
    changed_lines = sum(
        1
        for line in diff.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    )
    spec_changed = "spec.yaml" in changed_files or any(
        path.startswith("domains/") and path.endswith("/spec.yaml") for path in changed_files
    )
    workflow_changed = any(path.startswith(".github/workflows/") for path in changed_files)
    policy_changed = any(path.startswith("tools/review/policy/") for path in changed_files)
    protected_hits = [
        path
        for path in changed_files
        if path.startswith(".github/workflows/") or path.startswith("tools/review/policy/")
    ]
    proposal_type = infer_change_type(changed_files)
    stable_input = json.dumps(
        {
            "base_ref": base_ref,
            "head_ref": head_ref,
            "changed_files": changed_files,
            "diff": diff,
        },
        sort_keys=True,
    )
    proposal_id = hashlib.sha256(stable_input.encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"proposal_{proposal_id}",
        "type": proposal_type,
        "changed_files": changed_files,
        "changed_lines": changed_lines,
        "diff": diff,
        "metadata": {
            "base_ref": base_ref,
            "head_ref": head_ref,
            "source": source,
            "spec_changed": spec_changed,
            "workflow_changed": workflow_changed,
            "policy_changed": policy_changed,
            "protected_path_hits": protected_hits,
            "generated_at": datetime.now(tz=UTC).isoformat(),
        },
    }


def build_context(base_ref: str, head_ref: str) -> dict[str, Any]:
    return build_change_proposal(base_ref=base_ref, head_ref=head_ref, source="git_pr")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = build_context(base_ref=args.base_ref, head_ref=args.head_ref)
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
