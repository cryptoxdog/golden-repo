#!/usr/bin/env python3
"""Validate every L9 canonical contract YAML against the meta-schema.

This verifier is the runtime check for the L9 docs/contracts scaffold added by
the `chore/l9-docs-contracts-scaffold` branch. It is intentionally separate
from `tools/verify_contracts.py`, which validates the *legacy* contract
manifest (SHA-256 + cursorrules/CLAUDE.md references).

Behaviour:
  * Walks `contracts/**/*.contract.yaml`.
  * Validates every file against `contracts/_schemas/l9_contract_meta.schema.json`.
  * Asserts the L9_META block is present and well-formed.
  * Checks for prohibited references to the superseded `PacketEnvelope` as a
    canonical type (allowed only inside the migration contract).

Exit codes:
  0 = all canonical contracts pass, OR no canonical contracts present yet.
  1 = one or more canonical contracts failed validation.

Tolerant mode:
  If `contracts/_schemas/l9_contract_meta.schema.json` is absent the script
  exits 0 with a NOTE. This lets the CI workflow run on `main` before the
  docs/contracts scaffold PR has merged.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - guarded by CI install step
    print("FAIL: jsonschema is required. pip install jsonschema>=4.21", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"
META_SCHEMA = CONTRACTS_DIR / "_schemas" / "l9_contract_meta.schema.json"
MIGRATION_CONTRACT = CONTRACTS_DIR / "transport" / "migration_from_packet_envelope.contract.yaml"

L9_META_RE = re.compile(r"^\s*#\s*L9_META\s*:?", re.MULTILINE)
PACKET_ENVELOPE_CANONICAL_RE = re.compile(
    r"\bcanonical\s*:\s*PacketEnvelope\b", re.IGNORECASE
)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return loaded


def _load_meta_schema() -> dict[str, Any]:
    with META_SCHEMA.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _has_l9_meta_header(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return bool(L9_META_RE.search(text))


def _check_packet_envelope_violation(path: Path) -> bool:
    """Return True if the file improperly declares PacketEnvelope as canonical."""
    if path.resolve() == MIGRATION_CONTRACT.resolve():
        return False
    text = path.read_text(encoding="utf-8")
    return bool(PACKET_ENVELOPE_CANONICAL_RE.search(text))


def _iter_contract_files() -> list[Path]:
    if not CONTRACTS_DIR.exists():
        return []
    return sorted(
        p for p in CONTRACTS_DIR.rglob("*.contract.yaml") if p.is_file()
    )


def main() -> int:
    print("=" * 64)
    print("L9 Canonical Contract Verification")
    print("=" * 64)

    if not CONTRACTS_DIR.exists():
        print("NOTE: contracts/ directory not present; nothing to verify.")
        return 0

    if not META_SCHEMA.exists():
        print(f"NOTE: meta-schema not found at {META_SCHEMA.relative_to(REPO_ROOT)};")
        print("      L9 canonical contracts pack has not landed on this branch yet.")
        print("RESULT: PASS (tolerant mode)")
        return 0

    contract_files = _iter_contract_files()
    if not contract_files:
        print("NOTE: no *.contract.yaml files under contracts/; nothing to verify.")
        print("RESULT: PASS")
        return 0

    schema = _load_meta_schema()
    validator = Draft202012Validator(schema)

    fails: list[str] = []
    passes: list[str] = []

    for path in contract_files:
        rel = path.relative_to(REPO_ROOT)

        # 1. L9_META header must be present.
        if not _has_l9_meta_header(path):
            fails.append(f"FAIL: {rel} is missing the L9_META header")
            continue

        # 2. YAML must parse and be a mapping.
        try:
            data = _load_yaml(path)
        except (yaml.YAMLError, ValueError) as exc:
            fails.append(f"FAIL: {rel} did not parse: {exc}")
            continue

        # 3. Schema validation against the meta-schema.
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            for err in errors:
                pointer = "/".join(str(p) for p in err.absolute_path) or "<root>"
                fails.append(f"FAIL: {rel} :: {pointer} :: {err.message}")
            continue

        # 4. Canonical-type discipline.
        if _check_packet_envelope_violation(path):
            fails.append(
                f"FAIL: {rel} declares PacketEnvelope as canonical; "
                "TransportPacket is canonical (see ADR-0001)."
            )
            continue

        passes.append(f"PASS: {rel}")

    for line in passes:
        print(f"  {line}")
    for line in fails:
        print(f"  {line}")

    print()
    print(f"Contracts validated: {len(passes)}/{len(contract_files)}")
    print(f"Failures:            {len(fails)}")

    if fails:
        print()
        print("RESULT: FAIL -- L9 canonical contract verification failed")
        return 1

    print()
    print("RESULT: PASS -- all L9 canonical contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
