"""Runtime enforcement of PacketEnvelope against the canonical contract."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml

from chassis.types import PacketEnvelope

logger = logging.getLogger(__name__)

_contract_cache: dict[str, dict[str, Any]] = {}


def load_contract(contracts_dir: str, contract_name: str) -> dict[str, Any]:
    cache_key = f"{contracts_dir}/{contract_name}"
    if cache_key in _contract_cache:
        return _contract_cache[cache_key]
    path = Path(contracts_dir) / f"{contract_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Contract not found: {path}")
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    data = cast(dict[str, Any], loaded)
    _contract_cache[cache_key] = data
    return data


def enforce_packet_contract(packet: PacketEnvelope, *, contracts_dir: str) -> list[str]:
    load_contract(contracts_dir, "packet_envelope_v1")
    violations: list[str] = []
    if not packet.packet_id:
        violations.append("packet_id is empty")
    if not packet.schema_version:
        violations.append("schema_version is empty")
    if packet.schema_version != "1.1":
        violations.append(f"schema_version mismatch: expected 1.1, got {packet.schema_version}")
    if not packet.source_node:
        violations.append("source_node is empty")
    if not packet.target_node:
        violations.append("target_node is empty")
    if not packet.correlation_id:
        violations.append("correlation_id is empty")
    if not packet.idempotency_key:
        violations.append("idempotency_key is empty")
    if not packet.tenant.tenant_id:
        violations.append("tenant.tenant_id is empty")
    if not packet.tenant.actor:
        violations.append("tenant.actor is empty")
    if not packet.tenant.originator:
        violations.append("tenant.originator is empty")
    if not packet.tenant.org_id:
        violations.append("tenant.org_id is empty")
    if packet.lineage.generation < 0:
        violations.append("lineage.generation is negative")
    if not packet.payload.action:
        violations.append("payload.action is empty")
    if not packet.security.content_hash:
        violations.append("security.content_hash is empty")
    if not packet.verify_content_hash():
        violations.append("security.content_hash does not match payload")
    if violations:
        logger.warning(
            "PacketEnvelope contract violations",
            extra={"violations": violations, "packet_id": packet.packet_id},
        )
    return violations
