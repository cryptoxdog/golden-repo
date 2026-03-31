from __future__ import annotations

from chassis.packet_envelope import PacketEnvelope


def delegate_action(packet: PacketEnvelope, *, target_node: str, action: str, payload: dict | None = None) -> PacketEnvelope:
    return packet.model_copy(update={
        "header": packet.header.model_copy(update={"packet_type": "delegation", "action": action}),
        "address": packet.address.model_copy(update={"destination_node": target_node}),
        "payload": payload or packet.payload,
    })
