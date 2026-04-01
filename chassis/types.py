from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class PacketType(str, Enum):
    execute = "execute"
    response = "response"
    error = "error"
    health = "health"
    audit = "audit"
    describe = "describe"


class TenantSection(BaseModel):
    actor: str = Field(..., min_length=1)
    on_behalf_of: str = Field(..., min_length=1)
    originator: str = Field(..., min_length=1)
    org_id: str = Field(..., min_length=1)

    model_config = {"frozen": True}


class LineageSection(BaseModel):
    root_id: str = Field(..., min_length=1)
    generation: int = Field(..., ge=0)
    parent_id: str | None = None

    model_config = {"frozen": True}


class SecuritySection(BaseModel):
    content_hash: str = Field(..., min_length=1)
    envelope_hash: str = Field(..., min_length=1)
    signature: str | None = None
    classification: str = "internal"
    encryption_status: str = "plaintext"
    pii_fields: list[str] = Field(default_factory=list)


class GovernanceSection(BaseModel):
    ttl_seconds: int | None = None
    priority: int = 5
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    dlq_target: str | None = None


class TraceEntry(BaseModel):
    node: str
    action: str
    timestamp: str
    duration_ms: float | None = None
    status: str = "ok"


class PacketEnvelope(BaseModel):
    # identity
    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    packet_type: PacketType = PacketType.execute
    schema_version: str = Field(default="1.1", pattern=r"^\d+\.\d+$")
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # routing
    source_node: str = Field(..., min_length=1)
    destination_node: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)

    # tenant (immutable by model_config frozen=False but enforced via validator)
    tenant: TenantSection

    # payload
    payload: dict[str, Any] = Field(default_factory=dict)

    # lineage
    lineage: LineageSection

    # security (computed)
    security: SecuritySection | None = None

    # governance
    governance: GovernanceSection = Field(default_factory=GovernanceSection)

    # trace (mutable list for hop appends)
    trace: list[TraceEntry] = Field(default_factory=list)

    # correlation for distributed tracing
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.1":
            raise ValueError(f"schema_version must be '1.1', got '{v}'")
        return v

    @model_validator(mode="after")
    def compute_security_hashes(self) -> "PacketEnvelope":
        content_hash = _sha256_canonical(self.payload)
        envelope_data = {
            "packet_id": self.packet_id,
            "packet_type": self.packet_type.value,
            "schema_version": self.schema_version,
            "idempotency_key": self.idempotency_key,
            "timestamp": self.timestamp,
            "source_node": self.source_node,
            "destination_node": self.destination_node,
            "action": self.action,
            "tenant": self.tenant.model_dump(),
            "payload": self.payload,
            "lineage": self.lineage.model_dump(),
            "correlation_id": self.correlation_id,
        }
        envelope_hash = _sha256_canonical(envelope_data)
        self.security = SecuritySection(
            content_hash=content_hash,
            envelope_hash=envelope_hash,
            signature=self.security.signature if self.security else None,
            classification=(
                self.security.classification if self.security else "internal"
            ),
            encryption_status=(
                self.security.encryption_status if self.security else "plaintext"
            ),
            pii_fields=self.security.pii_fields if self.security else [],
        )
        return self

    def derive(
        self,
        *,
        action: str,
        destination_node: str,
        payload: dict[str, Any],
        packet_type: PacketType = PacketType.execute,
    ) -> "PacketEnvelope":
        return PacketEnvelope(
            packet_type=packet_type,
            schema_version="1.1",
            idempotency_key=str(uuid.uuid4()),
            source_node=self.destination_node,
            destination_node=destination_node,
            action=action,
            tenant=self.tenant,
            payload=payload,
            lineage=LineageSection(
                root_id=self.lineage.root_id,
                generation=self.lineage.generation + 1,
                parent_id=self.packet_id,
            ),
            governance=self.governance,
            correlation_id=self.correlation_id,
        )

    def append_trace(self, node: str, action: str, duration_ms: float | None = None, status: str = "ok") -> None:
        self.trace.append(
            TraceEntry(
                node=node,
                action=action,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                status=status,
            )
        )

    def verify_content_hash(self) -> bool:
        if self.security is None:
            return False
        expected = _sha256_canonical(self.payload)
        return self.security.content_hash == expected


def _sha256_canonical(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def build_root_packet(
    *,
    source_node: str,
    destination_node: str,
    action: str,
    tenant: TenantSection,
    payload: dict[str, Any],
    packet_type: PacketType = PacketType.execute,
    idempotency_key: str | None = None,
) -> PacketEnvelope:
    root_id = str(uuid.uuid4())
    return PacketEnvelope(
        packet_type=packet_type,
        schema_version="1.1",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        source_node=source_node,
        destination_node=destination_node,
        action=action,
        tenant=tenant,
        payload=payload,
        lineage=LineageSection(root_id=root_id, generation=0, parent_id=None),
    )
