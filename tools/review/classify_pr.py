from __future__ import annotations

import argparse
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from tools.review.build_context import build_context

RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _raise_risk(current: str, candidate: str) -> str:
    return candidate if RISK_ORDER[candidate] > RISK_ORDER[current] else current


def classify(proposal: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
    changed_files: list[str] = proposal["changed_files"]
    changed_lines: int = proposal["changed_lines"]
    metadata = proposal.get("metadata", {})
    classes: set[str] = set()
    reasons: list[str] = []
    rules = policy["classification_rules"]

    def matches_rule(rule_name: str) -> bool:
        rule = rules[rule_name]
        include = rule.get("include", [])
        exclude = rule.get("exclude", [])
        if not changed_files:
            return False
        if not all(_matches_any(path, include) for path in changed_files):
            return False
        if exclude and any(_matches_any(path, exclude) for path in changed_files):
            return False
        return True

    if matches_rule("docs_only"):
        classes.add("docs_only")
    if matches_rule("ci_only"):
        classes.add("ci_only")
    if metadata.get("spec_changed"):
        classes.add("spec_change")
    if any(_matches_any(path, rules["engine_logic_change"]["include"]) for path in changed_files):
        classes.add("engine_logic_change")
    if matches_rule("tests_only"):
        classes.add("tests_only")

    risk = "low"
    for path in changed_files:
        if _matches_any(path, policy["risk_routing"]["critical_paths"]):
            risk = _raise_risk(risk, "critical")
            reasons.append(f"Matched critical path: {path}")
        elif _matches_any(path, policy["risk_routing"]["high_risk_paths"]):
            risk = _raise_risk(risk, "high")
            reasons.append(f"Matched high risk path: {path}")
        elif _matches_any(path, policy["risk_routing"]["low_risk_paths"]):
            reasons.append(f"Matched low risk path: {path}")
        else:
            risk = _raise_risk(risk, "medium")
            reasons.append(f"Matched default medium risk path: {path}")

    if changed_lines > policy["size_limits"]["max_changed_lines_for_autonomous_review"]:
        risk = _raise_risk(risk, "high")
        reasons.append("Exceeded max_changed_lines_for_autonomous_review")

    semantic_cfg = policy["semantic_review"]
    run_semantic = semantic_cfg["enabled"] and risk in semantic_cfg["trigger_on"]
    if any(item in classes for item in semantic_cfg["skip_on"]):
        run_semantic = False
    if "spec_change" in classes and semantic_cfg["enabled"]:
        run_semantic = True
    if "engine_logic_change" in classes and semantic_cfg["enabled"]:
        run_semantic = True

    return {
        "proposal_id": proposal["id"],
        "classes": sorted(classes),
        "risk": risk,
        "run_semantic_review": run_semantic,
        "changed_files": changed_files,
        "reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=False)
    parser.add_argument("--head-ref", required=False)
    parser.add_argument("--proposal", required=False)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.proposal:
        proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    else:
        if not args.base_ref or not args.head_ref:
            msg = "Either --proposal or both --base-ref/--head-ref are required"
            raise ValueError(msg)
        proposal = build_context(args.base_ref, args.head_ref)

    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    result = classify(proposal, policy)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
