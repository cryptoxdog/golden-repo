# --- L9_META ---
# l9_schema: 1
# origin: golden-repo
# engine: golden-repo
# layer: [test, compliance]
# tags: [test, compliance, logging, principal_id, pii, adr_0003]
# owner: platform
# status: active
# --- /L9_META ---
"""Compliance test: no log record may carry a raw ``principal_id``.

Asserted properties (ADR-0003 §"Consequences" → PII discipline):

1. **Source-level guard.** ``chassis/logging.hash_principal_id_processor``
   must always replace the raw ``principal_id`` with ``principal_id_hash``
   when it runs. Verified end-to-end for representative records.
2. **Codebase guard.** No production source file under ``chassis/``,
   ``engine/``, or ``domains/`` writes a literal log record containing the
   key ``"principal_id"`` *without* the hashing processor. We approximate
   this with a focused grep — fixture files under ``tests/fixtures/`` are
   excluded.
3. **Fixture guard.** Any captured log fixture under
   ``tests/fixtures/log_samples/`` (if the directory exists) must not
   contain a raw ``principal_id`` key.

These tests embody the "log records never ship raw identity" invariant
declared in ``contracts/governance/tenant_context.contract.yaml``
(``invariants: principal_id_never_logged_raw``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from chassis.logging import (
    PRINCIPAL_ID_FIELD,
    PRINCIPAL_ID_HASH_FIELD,
    assert_no_raw_principal_id,
    hash_principal_id_processor,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "log_samples"


# ── 1. source-level processor guard ────────────────────────────────────


def test_processor_strips_raw_principal_id_for_representative_record() -> None:
    record = {
        "event": "http_request",
        "method": "POST",
        "path": "/v1/execute",
        "status_code": 200,
        PRINCIPAL_ID_FIELD: "user_alice",
    }
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert PRINCIPAL_ID_HASH_FIELD in out
    assert_no_raw_principal_id(out)


def test_processor_run_via_install_chain_strips_raw_value() -> None:
    """Simulate the full structlog chain run: hash processor → renderer."""
    from chassis.logging import install_pii_processors

    record = {"event": "audit", PRINCIPAL_ID_FIELD: "user_alice"}
    chain = install_pii_processors([])
    for proc in chain:
        record = proc(None, "info", record)
    assert_no_raw_principal_id(record)


# ── 2. codebase guard ──────────────────────────────────────────────────


_SOURCE_DIRS = ["chassis", "engine", "domains"]
# Allowed direct uses of the literal "principal_id":
#   - the chassis/logging.py module itself (it owns the constant)
#   - chassis/middleware/principal.py (sets it on request.state)
#   - chassis/types.py (declares the Pydantic field)
_ALLOWED_FILES = {
    "chassis/logging.py",
    "chassis/middleware/principal.py",
    "chassis/middleware/__init__.py",
    "chassis/types.py",
}
_LOG_LITERAL_RE = re.compile(
    r"""(logger|log)\s*\.\s*(debug|info|warning|warn|error|exception|critical|log)\s*\([^)]*['"]principal_id['"]""",
    re.IGNORECASE,
)


def _python_files() -> list[Path]:
    out: list[Path] = []
    for d in _SOURCE_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            out.extend(p for p in base.rglob("*.py") if p.is_file())
    return out


def test_no_production_source_logs_a_literal_principal_id_key() -> None:
    """No production logger.* call ships a literal 'principal_id' key.

    Allow the modules that own the constant declaration (see _ALLOWED_FILES).
    The intent is to catch ad-hoc ``logger.info("...", principal_id=...)``
    callsites that bypass the structlog chain.
    """
    offenders: list[str] = []
    for path in _python_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _ALLOWED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for match in _LOG_LITERAL_RE.finditer(text):
            offenders.append(f"{rel}: {match.group(0)!r}")
    assert offenders == [], (
        "log callsites referencing literal 'principal_id' bypass the structlog "
        "PII processor:\n  " + "\n  ".join(offenders)
    )


# ── 3. fixture guard ──────────────────────────────────────────────────


def _iter_log_fixtures() -> list[Path]:
    if not LOG_FIXTURES_DIR.exists():
        return []
    return sorted(p for p in LOG_FIXTURES_DIR.rglob("*.json") if p.is_file())


@pytest.mark.skipif(
    not LOG_FIXTURES_DIR.exists(),
    reason="No log_samples fixture directory; nothing to scan.",
)
def test_no_log_fixture_contains_raw_principal_id() -> None:
    fixtures = _iter_log_fixtures()
    if not fixtures:
        pytest.skip("log_samples directory exists but is empty")
    offenders: list[str] = []
    for path in fixtures:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        records = data if isinstance(data, list) else [data]
        for record in records:
            if isinstance(record, dict) and record.get(PRINCIPAL_ID_FIELD):
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
                break
    assert offenders == [], (
        "log fixtures carry raw 'principal_id' values:\n  " + "\n  ".join(offenders)
    )
