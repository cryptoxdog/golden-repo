"""
tools/auditors/spec_fidelity.py

Spec Intent Fidelity Validator — Dimension 3.

Validates:
  1. spec.yaml is structurally valid against spec_schema.json
  2. All spec actions have registered handlers
  3. No unauthorized handlers exist (handlers not in spec)
  4. Handler action coverage ratio

Usage:
    python tools/auditors/spec_fidelity.py \
        --spec spec.yaml \
        --handlers-dir engine/handlers \
        --schema tools/review/policy/spec_schema.json \
        --output spec_fidelity_report.json

Exit codes: 0 = clean/warn, 1 = block, 2 = error
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


# ── Handler extraction ────────────────────────────────────────────────────────

def extract_registered_handlers(handlers_path: Path) -> set[str]:
    """
    Extract all handle_* registered functions from engine/handlers.py or
    handlers/__init__.py HANDLER_MAP.
    """
    registered: set[str] = set()

    if handlers_path.is_file():
        files = [handlers_path]
    elif handlers_path.is_dir():
        files = list(handlers_path.glob("**/*.py"))
    else:
        return registered

    for filepath in files:
        try:
            with filepath.open() as f:
                tree = ast.parse(f.read())
        except (SyntaxError, OSError):
            continue

        for node in ast.walk(tree):
            # Pattern 1: HANDLER_MAP = {"action": handle_action}
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        registered.add(key.value)

            # Pattern 2: registry["action"] = handle_action
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and isinstance(target.slice.value, str)
                    ):
                        registered.add(target.slice.value)

            # Pattern 3: async def handle_* functions
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                if node.name.startswith("handle_"):
                    action = node.name[len("handle_"):]
                    registered.add(action)

    return registered


# ── Spec loading ──────────────────────────────────────────────────────────────

def load_spec(spec_path: Path) -> dict[str, Any]:
    with spec_path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{spec_path}: spec must be a YAML mapping")
    return data


# ── Schema validation ─────────────────────────────────────────────────────────

def validate_spec_schema(spec: dict, schema_path: Path) -> list[str]:
    """Validate spec against JSON Schema. Returns list of error strings."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed — schema validation skipped"]

    try:
        with schema_path.open() as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Could not load schema: {exc}"]

    errors: list[str] = []
    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(spec):
        errors.append(f"{list(error.absolute_path)}: {error.message}")
    return errors


# ── Coverage check ────────────────────────────────────────────────────────────

def check_spec_action_coverage(
    spec: dict,
    registered: set[str],
) -> dict[str, Any]:
    """Compare spec actions against registered handlers."""
    spec_actions: set[str] = set()

    # Support multiple spec formats
    for action in spec.get("actions", []):
        if isinstance(action, dict):
            spec_actions.add(action.get("name", ""))
        elif isinstance(action, str):
            spec_actions.add(action)

    # Also check top-level keys like 'handlers' or 'endpoints'
    for handler_name in spec.get("handlers", {}).keys():
        spec_actions.add(handler_name)

    spec_actions.discard("")

    missing = spec_actions - registered
    extra = registered - spec_actions

    return {
        "spec_actions": sorted(spec_actions),
        "registered_handlers": sorted(registered),
        "missing_implementations": sorted(missing),
        "unauthorized_handlers": sorted(extra),
        "coverage_ratio": (
            len(spec_actions & registered) / max(len(spec_actions), 1)
        ),
    }


# ── Confidence scoring ────────────────────────────────────────────────────────

def score_spec_fidelity(
    coverage: dict,
    schema_errors: list[str],
    ambiguity_score: int = 0,
) -> tuple[float, str]:
    """
    Asymmetric escalation:
    - Missing handler = BLOCK (missing capability)
    - Schema error = BLOCK (spec itself broken)
    - Ambiguity >= 2 = ESCALATE (human must resolve)
    - Unauthorized handler = WARN (over-interpretation)
    """
    if coverage["missing_implementations"]:
        return 0.98, "BLOCK"
    if schema_errors:
        return 0.95, "BLOCK"
    if ambiguity_score >= 2:
        return 0.60, "ESCALATE"
    if coverage["unauthorized_handlers"]:
        return 0.75, "WARN"
    if coverage["coverage_ratio"] >= 0.98:
        return 0.92, "APPROVE"
    return 0.70, "WARN"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Spec fidelity validator")
    parser.add_argument("--spec", default="spec.yaml")
    parser.add_argument("--handlers-dir", default="engine/handlers")
    parser.add_argument("--schema", default="tools/review/policy/spec_schema.json")
    parser.add_argument("--output", default="spec_fidelity_report.json")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    handlers_path = Path(args.handlers_dir)
    schema_path = Path(args.schema)
    output_path = Path(args.output)

    try:
        spec = load_spec(spec_path)
    except Exception as exc:
        print(f"ERROR: Could not load spec: {exc}", file=sys.stderr)
        return 2

    registered = extract_registered_handlers(handlers_path)
    coverage = check_spec_action_coverage(spec, registered)
    schema_errors = validate_spec_schema(spec, schema_path) if schema_path.exists() else []
    confidence, verdict = score_spec_fidelity(coverage, schema_errors)

    report = {
        "verdict": verdict,
        "confidence": confidence,
        "coverage": coverage,
        "schema_errors": schema_errors,
    }

    output_path.write_text(json.dumps(report, indent=2))
    print(
        f"verdict={verdict} coverage={coverage['coverage_ratio']:.2f} "
        f"missing={coverage['missing_implementations']} "
        f"schema_errors={len(schema_errors)}"
    )

    return 0 if verdict in ("APPROVE", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
