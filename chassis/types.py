"""PacketEnvelope — canonical L9 wire format with full contract compliance."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PacketType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    DELEGATION = "delegation"


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class TraceStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TenantInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str
    actor: str
    originator: str
    org_id: str
    on_behalf_of: str | None = None


class Lineage(BaseModel):
    root_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    generation: int = 0

    @field_validator("generation")
    @classmethod
    def generation_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("generation must be >= 0")
        return value


class TraceEntry(BaseModel):
    node: str
    timestamp: str
    action: str
    status: TraceStatus


class SecurityInfo(BaseModel):
    content_hash: str = ""
    envelope_hash: str | None = None
    signature: str | None = None
    classification: Classification = Classification.INTERNAL


class Governance(BaseModel):
    retention_days: int = 90
    audit_required: bool = True


class Payload(BaseModel):
    action: str
    data: dict[str, Any] = Field(default_factory=dict)


class PacketEnvelope(BaseModel):
    model_config = ConfigDict(frozen=False)

    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    packet_type: PacketType = PacketType.REQUEST
    schema_version: str = "1.1"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_node: str = ""
    target_node: str = ""
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant: TenantInfo
    lineage: Lineage = Field(default_factory=Lineage)
    payload: Payload
    security: SecurityInfo = Field(default_factory=SecurityInfo)
    governance: Governance = Field(default_factory=Governance)
    trace: list[TraceEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def compute_content_hash(self) -> PacketEnvelope:
        if not self.security.content_hash:
            raw = json.dumps(self.payload.model_dump(mode="json"), sort_keys=True)
            self.security.content_hash = hashlib.sha256(raw.encode()).hexdigest()
        return self

    def verify_content_hash(self) -> bool:
        raw = json.dumps(self.payload.model_dump(mode="json"), sort_keys=True)
        expected = hashlib.sha256(raw.encode()).hexdigest()
        return self.security.content_hash == expected

    def derive(
        self,
        *,
        new_action: str | None = None,
        new_target: str | None = None,
        source_node: str = "",
    ) -> PacketEnvelope:
        new_payload = self.payload.model_copy(update={"action": new_action} if new_action else {})
        new_lineage = Lineage(
            root_id=self.lineage.root_id,
            parent_id=self.packet_id,
            generation=self.lineage.generation + 1,
        )
        return PacketEnvelope(
            packet_type=self.packet_type,
            schema_version=self.schema_version,
            source_node=source_node or self.target_node,
            target_node=new_target or self.target_node,
            correlation_id=self.correlation_id,
            idempotency_key=str(uuid.uuid4()),
            tenant=self.tenant.model_copy(),
            lineage=new_lineage,
            payload=new_payload,
            governance=self.governance.model_copy(),
        )

    def append_trace(self, *, node: str, action: str, status: TraceStatus) -> None:
        self.trace.append(
            TraceEntry(
                node=node,
                timestamp=datetime.now(UTC).isoformat(),
                action=action,
                status=status,
            )
        )


def normalize_packet(raw: dict[str, Any], *, source_node: str = "unknown") -> PacketEnvelope:
    """Build a PacketEnvelope from an inbound raw dict, filling defaults."""
    tenant_raw = raw.get("tenant", {})
    tenant = TenantInfo(
        tenant_id=tenant_raw.get("tenant_id", ""),
        actor=tenant_raw.get("actor", ""),
        originator=tenant_raw.get("originator", ""),
        org_id=tenant_raw.get("org_id", ""),
        on_behalf_of=tenant_raw.get("on_behalf_of"),
    )
    payload_raw = raw.get("payload", {})
    payload = Payload(
        action=payload_raw.get("action", raw.get("action", "")),
        data=payload_raw.get("data", raw.get("parameters", {})),
    )
    return PacketEnvelope(
        packet_id=raw.get("packet_id", str(uuid.uuid4())),
        packet_type=raw.get("packet_type", PacketType.REQUEST),
        source_node=raw.get("source_node", source_node),
        target_node=raw.get("target_node", "self"),
        correlation_id=raw.get("correlation_id", str(uuid.uuid4())),
        idempotency_key=raw.get("idempotency_key", str(uuid.uuid4())),
        tenant=tenant,
        payload=payload,
    )
