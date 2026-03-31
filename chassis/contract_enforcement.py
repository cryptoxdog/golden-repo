from __future__ import annotations

from typing import Any

from app.contract_registry import load_contract_bundle


class ContractViolation(ValueError):
    pass


def enforce_packet_contract(raw_packet: dict[str, Any]) -> None:
    bundle = load_contract_bundle()

    header = raw_packet.get('header')
    if not isinstance(header, dict):
        raise ContractViolation('packet.header is required')

    schema_version = header.get('schema_version')
    if schema_version != bundle.packet_version:
        raise ContractViolation(
            f'packet schema_version must equal canonical protocol version {bundle.packet_version}, got {schema_version!r}'
        )

    packet_type = header.get('packet_type')
    if packet_type not in bundle.packet_types:
        raise ContractViolation(f'packet_type {packet_type!r} is not part of canonical protocol')

    mandatory_top_level = ('header', 'address', 'tenant', 'payload', 'security', 'governance', 'delegation_chain', 'hop_trace', 'lineage', 'attachments')
    for field in mandatory_top_level:
        if field not in raw_packet:
            raise ContractViolation(f'mandatory protocol field missing: {field}')


def enforce_registration_contract(registration_payload: dict[str, Any]) -> None:
    bundle = load_contract_bundle()
    required = set(bundle.required_registration_fields)
    missing = sorted(field for field in required if field not in registration_payload)
    if missing:
        raise ContractViolation(f'registration payload missing required fields: {", ".join(missing)}')
