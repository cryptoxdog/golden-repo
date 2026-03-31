from __future__ import annotations

from chassis.packet_envelope import PacketEnvelope


class ResponseParser:
    def parse(self, packet: PacketEnvelope | dict) -> dict:
        env = packet if isinstance(packet, PacketEnvelope) else PacketEnvelope.model_validate(packet)
        return {"ok": env.header.packet_type == "response", "payload": env.payload, "trace_id": env.header.trace_id}
