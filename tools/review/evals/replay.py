from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.review.aggregate import aggregate_reports


def load_cases(cases_path: Path) -> list[dict]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    return payload["cases"]


def evaluate(cases: list[dict], policy: dict) -> dict:
    results: list[dict] = []
    passed = 0
    for case in cases:
        aggregate = aggregate_reports(case["reports"], policy)
        ok = aggregate["final_verdict"] == case["expected_final_verdict"]
        if ok:
            passed += 1
        results.append(
            {
                "name": case["name"],
                "expected_final_verdict": case["expected_final_verdict"],
                "actual_final_verdict": aggregate["final_verdict"],
                "passed": ok,
            }
        )
    return {
        "case_count": len(cases),
        "passed_count": passed,
        "failed_count": len(cases) - passed,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = json.loads(Path(args.policy).read_text(encoding="utf-8")) if args.policy.endswith(".json") else None
    if policy is None:
        import yaml
        policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    cases = load_cases(Path(args.cases))
    result = evaluate(cases, policy)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
