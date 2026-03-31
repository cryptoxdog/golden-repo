from __future__ import annotations

from typing import Any, Callable

from app.config import get_config
from .packet_envelope import PacketEnvelope
from .security import verify_signature, ValidationFailure

_HANDLERS: dict[str, Callable[..., Any]] = {}


def register_handler(action: str, fn: Callable[..., Any]) -> None:
    _HANDLERS[action.strip().lower()] = fn


def inflate_ingress(raw: dict[str, Any]) -> PacketEnvelope:
    packet = PacketEnvelope.model_validate(raw)
    cfg = get_config()
    if packet.address.destination_node != cfg.node_name:
        raise ValidationFailure("packet destination does not match this node")
    if packet.header.action not in cfg.allowed_actions:
        raise ValidationFailure("action not allowed")
    if packet.header.packet_type not in cfg.allowed_packet_types:
        raise ValidationFailure("packet_type not allowed")
    if cfg.require_signature and not verify_signature(packet):
        raise ValidationFailure("invalid signature")
    return packet


async def execute_handler(packet: PacketEnvelope) -> PacketEnvelope:
    fn = _HANDLERS[packet.header.action]
    result = await fn(packet.tenant.org_id, packet.payload)
    return packet.model_copy(update={
        "header": packet.header.model_copy(update={"packet_type": "response"}),
        "address": packet.address.model_copy(update={"destination_node": packet.address.reply_to, "reply_to": packet.address.destination_node}),
        "payload": result,
    })
