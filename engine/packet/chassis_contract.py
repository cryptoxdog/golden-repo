from __future__ import annotations

from typing import Any

from chassis.packet_envelope import PacketEnvelope, create_packet


def build_request_packet(*, action: str, payload: dict[str, Any], tenant: str | dict[str, Any], destination_node: str, source_node: str = "client", reply_to: str = "client") -> PacketEnvelope:
    return create_packet(action=action, payload=payload, tenant=tenant, destination_node=destination_node, source_node=source_node, reply_to=reply_to)


def inflate_ingress(raw_dict: dict[str, Any]) -> PacketEnvelope:
    return PacketEnvelope.model_validate(raw_dict)


def deflate_egress(packet_or_request: PacketEnvelope, response_data: dict[str, Any] | None = None) -> dict[str, Any]:
    if response_data is None:
        return packet_or_request.dict()
    response = packet_or_request.model_copy(update={
        "header": packet_or_request.header.model_copy(update={"packet_type": "response"}),
        "payload": {"status": "success", "data": response_data},
        "address": packet_or_request.address.model_copy(update={"destination_node": packet_or_request.address.reply_to}),
    })
    return response.dict()
