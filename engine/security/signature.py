from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from chassis.types import PacketEnvelope

logger = logging.getLogger(__name__)


class SignatureError(Exception):
    pass


def verify_hmac_sha256(packet: PacketEnvelope, secret: str) -> None:
    if packet.security is None:
        raise SignatureError("security section absent — cannot verify signature")
    if not packet.security.signature:
        raise SignatureError("packet.security.signature is absent")
    expected = hmac.new(
        secret.encode(),
        packet.security.envelope_hash.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(packet.security.signature, expected):
        raise SignatureError("HMAC-SHA256 signature mismatch")
    logger.debug("signature_verified", extra={"packet_id": packet.packet_id})


def sign_hmac_sha256(packet: PacketEnvelope, secret: str) -> str:
    if packet.security is None:
        raise SignatureError("security section absent — cannot sign packet")
    signature = hmac.new(
        secret.encode(),
        packet.security.envelope_hash.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature
