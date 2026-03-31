from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from chassis.packet_envelope import PacketEnvelope


class PacketExecutionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    action: str
    org_id: str
    source_node: str
    trace_id: str | None

    @classmethod
    def from_packet(cls, packet: PacketEnvelope) -> "PacketExecutionContext":
        return cls(action=packet.header.action, org_id=packet.tenant.org_id, source_node=packet.address.source_node, trace_id=packet.header.trace_id)
