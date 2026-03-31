from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.review.build_context import build_change_proposal


def build_pr_proposal(base_ref: str, head_ref: str) -> dict:
    return build_change_proposal(base_ref=base_ref, head_ref=head_ref, source="git_pr")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    proposal = build_pr_proposal(base_ref=args.base_ref, head_ref=args.head_ref)
    Path(args.output).write_text(json.dumps(proposal, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
