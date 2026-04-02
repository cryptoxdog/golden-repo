from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def verify_signature(payload_bytes: bytes, secret: str, expected: str) -> bool:
    computed = sign_payload(payload_bytes, secret)
    result = hmac.compare_digest(computed, expected)
    if not result:
        logger.warning("signature_verification_failed")
    return result
