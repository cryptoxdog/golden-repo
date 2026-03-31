from __future__ import annotations

from chassis.packet_envelope import create_packet
from client.auth import sign_outbound_packet


class PacketBuilder:
    def build(self, *, action: str, payload: dict, tenant, destination_node: str, source_node: str = "client", reply_to: str | None = None):
        packet = create_packet(action=action, payload=payload, tenant=tenant, destination_node=destination_node, source_node=source_node, reply_to=reply_to or source_node)
        return sign_outbound_packet(packet)
