# --- L9_META ---
# l9_schema: 1
# origin: chassis
# engine: "*"
# layer: [observability, security, pii]
# tags: [chassis, logging, structlog, principal_id, pii, hashing]
# owner: platform
# status: active
# --- /L9_META ---
"""chassis/logging — structured-logging processors for L9 nodes.

This module owns the structlog processor chain entries that enforce L9
PII discipline at the log boundary. Today it owns one processor:

* ``hash_principal_id_processor``  — replaces any ``principal_id`` field on
  a log record with ``principal_id_hash`` (SHA-256 hex) before the record
  reaches any sink. Idempotent.

The processor is registered into the structlog chain by
``chassis/chassis_app.py:build_app``. It MUST be installed before any
emitter that ships records to a sink (Datadog, Splunk, ELK, CloudWatch).

Related contracts:

* ``contracts/governance/tenant_context.contract.yaml`` — declares the
  field ``principal_id`` as ``pii: hashed``.
* ``contracts/observability/metrics.contract.yaml`` — defines
  ``principal_id_present_total`` (counter; SLI for the rollout).

See ADR-0003 for rationale and the full rollout plan.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, Iterable, Mapping

logger = logging.getLogger(__name__)

# Public field names. Kept here so callers and tests reference one
# canonical definition (kernel-3 contract 1: no string magic).
PRINCIPAL_ID_FIELD = "principal_id"
PRINCIPAL_ID_HASH_FIELD = "principal_id_hash"


def _sha256_hex(value: str) -> str:
    """Return the lowercase SHA-256 hex digest of ``value`` UTF-8 encoded."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_principal_id_processor(
    logger_obj: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor: hash ``principal_id`` to ``principal_id_hash``.

    Behaviour:

    * If ``event_dict`` contains a non-empty string ``principal_id``, the
      raw value is removed from the record and an SHA-256 hex digest is
      written to ``principal_id_hash``. If ``principal_id_hash`` is
      already present, it is preserved (idempotent).
    * If ``principal_id`` is absent or empty, the record is returned
      unchanged.
    * If ``principal_id`` is present but is not a string (e.g. a stray
      ``None``), it is dropped silently to avoid type-leakage into sinks.

    Args:
        logger_obj: Bound structlog logger. Unused; required by the
            structlog processor signature.
        method_name: Name of the logging method that emitted the record.
            Unused; required by the structlog processor signature.
        event_dict: The mutable event dictionary structlog assembles for
            this record.

    Returns:
        The (mutated) ``event_dict``.
    """
    raw = event_dict.pop(PRINCIPAL_ID_FIELD, None)

    if not isinstance(raw, str) or raw == "":
        # Either absent, empty, or a non-string sentinel. Don't emit.
        return event_dict

    # Idempotent: if a downstream callsite already supplied the hash
    # field, prefer the explicit one.
    event_dict.setdefault(PRINCIPAL_ID_HASH_FIELD, _sha256_hex(raw))
    return event_dict


def install_pii_processors(processors: Iterable[Callable[..., Any]]) -> list[Callable[..., Any]]:
    """Return a copy of ``processors`` with the PII processors prepended.

    Helper used by ``chassis/chassis_app.py:build_app`` to keep ordering
    centralised. The processor list returned is suitable for
    ``structlog.configure(processors=...)``.

    The PII processors are placed before any rendering / JSON-emit
    processor so the raw value never reaches a renderer.
    """
    pii_chain: list[Callable[..., Any]] = [hash_principal_id_processor]
    return pii_chain + list(processors)


def assert_no_raw_principal_id(record: Mapping[str, Any]) -> None:
    """Compliance guard: raise if a record carries a raw ``principal_id``.

    Used in tests under ``tests/compliance/``. Production code paths run
    the processor, so this assertion mirrors what an auditor would assert
    on a captured log payload.
    """
    if PRINCIPAL_ID_FIELD in record and record[PRINCIPAL_ID_FIELD]:
        raise AssertionError(
            "compliance violation: log record carries a raw 'principal_id'; "
            "the structlog processor 'hash_principal_id_processor' must run "
            "before any sink emitter"
        )


__all__ = [
    "PRINCIPAL_ID_FIELD",
    "PRINCIPAL_ID_HASH_FIELD",
    "hash_principal_id_processor",
    "install_pii_processors",
    "assert_no_raw_principal_id",
]
