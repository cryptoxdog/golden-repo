"""HMAC-SHA256 signature generation and verification for PacketEnvelope."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def compute_hmac_sha256(payload: dict[str, Any], secret: str) -> str:
    raw = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def verify_hmac_sha256(payload: dict[str, Any], secret: str, signature: str) -> bool:
    expected = compute_hmac_sha256(payload, secret)
    return hmac.compare_digest(expected, signature)


def compute_envelope_hash(envelope_dict: dict[str, Any]) -> str:
    keys_for_hash = [
        "packet_id",
        "packet_type",
        "schema_version",
        "timestamp",
        "source_node",
        "target_node",
        "correlation_id",
        "idempotency_key",
    ]
    subset = {key: envelope_dict.get(key, "") for key in keys_for_hash}
    raw = json.dumps(subset, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()
