from __future__ import annotations

import argparse
from fnmatch import fnmatch
import json
from pathlib import Path

import yaml

from tools.review.build_context import build_context


RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _raise_risk(current: str, candidate: str) -> str:
    return candidate if RISK_ORDER[candidate] > RISK_ORDER[current] else current


def classify(context: dict, policy: dict) -> dict:
    changed_files: list[str] = context["changed_files"]
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
    if context["spec_changed"]:
        classes.add("spec_change")
    if any(_matches_any(path, rules["engine_logic_change"]["include"]) for path in changed_files):
        classes.add("engine_logic_change")
    if matches_rule("tests_only"):
        classes.add("tests_only")

    risk = "low"
    if changed_files:
        risk = "medium"

    if len(changed_files) > policy["size_limits"]["max_changed_files_for_autonomous_review"]:
        risk = _raise_risk(risk, "critical")
        reasons.append("PR exceeds autonomous review file-count limit")
    if context["changed_lines"] > policy["size_limits"]["max_changed_lines_for_autonomous_review"]:
        risk = _raise_risk(risk, "critical")
        reasons.append("PR exceeds autonomous review line-count limit")

    for path in changed_files:
        if _matches_any(path, policy["risk_routing"]["critical_paths"]):
            risk = _raise_risk(risk, "critical")
            reasons.append(f"Matched critical path: {path}")
        elif _matches_any(path, policy["risk_routing"]["high_risk_paths"]):
            risk = _raise_risk(risk, "high")
            reasons.append(f"Matched high risk path: {path}")

    semantic_cfg = policy["semantic_review"]
    semantic_triggers = set(semantic_cfg["trigger_on"])
    skip_classes = set(semantic_cfg["skip_on"])

    run_semantic_review = (
        semantic_cfg["enabled"]
        and not classes.intersection(skip_classes)
        and (
            risk in semantic_triggers
            or "spec_change" in classes and "spec_change" in semantic_triggers
            or "engine_logic_change" in classes and "engine_logic_change" in semantic_triggers
        )
        and context["changed_lines"] <= policy["size_limits"]["max_changed_lines_for_semantic_review"]
    )

    if risk == "critical":
        reasons.append("Critical risk classification requires human-aware merge path")

    return {
        "classes": sorted(classes),
        "risk": risk,
        "run_semantic_review": run_semantic_review,
        "changed_files": changed_files,
        "reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    context = build_context(args.base_ref, args.head_ref)
    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    result = classify(context, policy)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
