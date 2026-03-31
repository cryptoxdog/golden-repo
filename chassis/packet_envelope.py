from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .tenant_context import TenantContext, ensure_tenant_context


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


class PacketHeader(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    packet_id: UUID = Field(default_factory=uuid4)
    packet_type: str
    action: str
    priority: int = 2
    created_at: datetime = Field(default_factory=utc_now)
    timeout_ms: int = 30000
    schema_version: str = "1.1"
    idempotency_key: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    causation_id: UUID | None = None
    retry_count: int = 0
    replay_mode: bool = False


class PacketAddress(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_node: str
    destination_node: str
    reply_to: str


class PacketSecurity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    content_hash: str
    envelope_hash: str
    signature: str | None = None
    signature_algorithm: str | None = None
    signing_key_id: str | None = None
    classification: str = "internal"
    encryption_status: str = "plaintext"
    pii_fields: tuple[str, ...] = ()


class PacketGovernance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    intent: str
    compliance_tags: tuple[str, ...] = ()
    retention_days: int = 90
    redaction_applied: bool = False
    audit_required: bool = False
    data_subject_id: str | None = None


class PacketLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parent_id: UUID | None = None
    root_id: UUID
    generation: int = 0


class PacketEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    header: PacketHeader
    address: PacketAddress
    tenant: TenantContext
    payload: dict[str, Any]
    security: PacketSecurity
    governance: PacketGovernance
    delegation_chain: tuple[dict, ...] = ()
    hop_trace: tuple[dict, ...] = ()
    lineage: PacketLineage
    attachments: tuple[dict, ...] = ()

    def dict(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault("mode", "json")
        kwargs.setdefault("exclude_none", True)
        return self.model_dump(*args, **kwargs)


def compute_envelope_hash(packet: PacketEnvelope) -> str:
    payload = {
        "header": packet.header.model_dump(mode="json"),
        "address": packet.address.model_dump(mode="json"),
        "tenant": packet.tenant.model_dump(mode="json"),
        "payload": packet.payload,
        "governance": packet.governance.model_dump(mode="json"),
        "delegation_chain": packet.delegation_chain,
        "lineage": packet.lineage.model_dump(mode="json"),
        "attachments": packet.attachments,
        "content_hash": packet.security.content_hash,
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def create_packet(action: str, payload: dict[str, Any], tenant: str | dict | TenantContext, destination_node: str, *, source_node: str = "client", reply_to: str = "client") -> PacketEnvelope:
    packet_id = uuid4()
    tenant_ctx = ensure_tenant_context(tenant)
    header = PacketHeader(packet_type="request", action=action, trace_id=str(packet_id), correlation_id=str(packet_id))
    address = PacketAddress(source_node=source_node, destination_node=destination_node, reply_to=reply_to)
    sec = PacketSecurity(content_hash=compute_content_hash(payload), envelope_hash="0" * 64)
    env = PacketEnvelope(
        header=header,
        address=address,
        tenant=tenant_ctx,
        payload=payload,
        security=sec,
        governance=PacketGovernance(intent=action),
        lineage=PacketLineage(root_id=packet_id),
    )
    env2 = env.model_copy(update={"security": env.security.model_copy(update={"envelope_hash": compute_envelope_hash(env)})})
    return env2
