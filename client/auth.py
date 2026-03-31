from __future__ import annotations

from app.config import get_config
from chassis.packet_envelope import PacketEnvelope
from chassis.security import sign_packet


def sign_outbound_packet(packet: PacketEnvelope) -> PacketEnvelope:
    cfg = get_config()
    key = cfg.signing_private_key if cfg.signing_algorithm == "ed25519" else cfg.signing_key
    if not key:
        return packet
    return sign_packet(packet, key=key, key_id=cfg.signing_key_id, algorithm=cfg.signing_algorithm)
