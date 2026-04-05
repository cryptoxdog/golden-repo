"""Data classification enforcement for PacketEnvelope payloads."""

from __future__ import annotations

from typing import Any

from chassis.types import Classification, PacketEnvelope

RESTRICTED_FIELDS = {"ssn", "password", "secret", "token", "private_key", "credit_card"}
CONFIDENTIAL_FIELDS = {"email", "phone", "address", "dob", "date_of_birth"}


def detect_classification(data: dict[str, Any]) -> Classification:
    keys_lower = {key.lower() for key in _flatten_keys(data)}
    if keys_lower & RESTRICTED_FIELDS:
        return Classification.RESTRICTED
    if keys_lower & CONFIDENTIAL_FIELDS:
        return Classification.CONFIDENTIAL
    return Classification.INTERNAL


def enforce_classification(packet: PacketEnvelope) -> list[str]:
    violations: list[str] = []
    detected = detect_classification(packet.payload.data)
    current = packet.security.classification
    classification_order = [
        Classification.PUBLIC,
        Classification.INTERNAL,
        Classification.CONFIDENTIAL,
        Classification.RESTRICTED,
    ]
    if classification_order.index(detected) > classification_order.index(current):
        violations.append(f"Classification underrated: detected {detected.value}, marked as {current.value}")
    return violations


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    keys: list[str] = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.append(full_key)
        if isinstance(value, dict):
            keys.extend(_flatten_keys(value, full_key))
    return keys
