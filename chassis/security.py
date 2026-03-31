from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from app.config import get_config
from .packet_envelope import PacketEnvelope, compute_content_hash, compute_envelope_hash


class ValidationFailure(Exception):
    pass


def _coerce_bytes(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    try:
        return base64.b64decode(value, validate=True)
    except Exception:  # noqa: BLE001
        return value.encode("utf-8")


def sign_packet(packet: PacketEnvelope, *, key: str | bytes, key_id: str, algorithm: str) -> PacketEnvelope:
    pkt = recompute_hashes(packet)
    raw = _coerce_bytes(key)
    if algorithm == "hmac-sha256":
        sig = hmac.new(raw, pkt.security.envelope_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    else:
        sig = Ed25519PrivateKey.from_private_bytes(raw).sign(pkt.security.envelope_hash.encode("utf-8")).hex()
    return pkt.model_copy(update={"security": pkt.security.model_copy(update={"signature": sig, "signature_algorithm": algorithm, "signing_key_id": key_id})})


def verify_signature(packet: PacketEnvelope, *, key_resolver: Mapping[str, str] | None = None) -> bool:
    if packet.security.signature is None or packet.security.signature_algorithm is None:
        return False
    cfg = get_config()
    key_map = dict(cfg.verifying_keys)
    if key_resolver:
        key_map.update(key_resolver)
    raw = _coerce_bytes(key_map[packet.security.signing_key_id])
    if packet.security.signature_algorithm == "hmac-sha256":
        expected = hmac.new(raw, packet.security.envelope_hash.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, packet.security.signature)
    try:
        Ed25519PublicKey.from_public_bytes(raw).verify(bytes.fromhex(packet.security.signature), packet.security.envelope_hash.encode("utf-8"))
        return True
    except InvalidSignature:
        return False


def recompute_hashes(packet: PacketEnvelope) -> PacketEnvelope:
    pkt = packet.model_copy(update={"security": packet.security.model_copy(update={"content_hash": compute_content_hash(packet.payload), "envelope_hash": "0" * 64, "signature": None, "signature_algorithm": None})})
    return pkt.model_copy(update={"security": pkt.security.model_copy(update={"envelope_hash": compute_envelope_hash(pkt)})})


def export_ed25519_public_key(private_key_b64: str) -> str:
    raw = _coerce_bytes(private_key_b64)
    return base64.b64encode(Ed25519PrivateKey.from_private_bytes(raw).public_key().public_bytes_raw()).decode("ascii")
