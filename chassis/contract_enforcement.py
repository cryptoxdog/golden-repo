from __future__ import annotations

import logging
from typing import Any

from chassis.types import PacketEnvelope

logger = logging.getLogger(__name__)


class ContractViolation(Exception):
    pass


def enforce_packet_contract(packet: PacketEnvelope) -> None:
    errors: list[str] = []

    if not packet.packet_id:
        errors.append("packet_id is empty")
    if not packet.schema_version or packet.schema_version != "1.1":
        errors.append(f"schema_version must be '1.1', got '{packet.schema_version}'")
    if not packet.idempotency_key:
        errors.append("idempotency_key is empty")
    if not packet.source_node:
        errors.append("source_node is empty")
    if not packet.destination_node:
        errors.append("destination_node is empty")
    if not packet.action:
        errors.append("action is empty")

    t = packet.tenant
    if not t.actor:
        errors.append("tenant.actor is empty")
    if not t.on_behalf_of:
        errors.append("tenant.on_behalf_of is empty")
    if not t.originator:
        errors.append("tenant.originator is empty")
    if not t.org_id:
        errors.append("tenant.org_id is empty")

    if packet.lineage.generation < 0:
        errors.append("lineage.generation must be >= 0")
    if not packet.lineage.root_id:
        errors.append("lineage.root_id is empty")

    if packet.security is None:
        errors.append("security section is absent")
    else:
        if not packet.security.content_hash:
            errors.append("security.content_hash is empty")
        if not packet.security.envelope_hash:
            errors.append("security.envelope_hash is empty")
        if not packet.verify_content_hash():
            errors.append("security.content_hash does not match payload")

    if errors:
        msg = "; ".join(errors)
        logger.error("contract_violation", extra={"errors": errors, "packet_id": packet.packet_id})
        raise ContractViolation(f"PacketEnvelope contract violation: {msg}")

    logger.debug("contract_enforced", extra={"packet_id": packet.packet_id})
