# --- L9_META ---
# l9_schema: 1
# origin: golden-repo
# engine: golden-repo
# layer: [chassis, types]
# tags: [chassis, types, tenant_context, principal_id]
# owner: platform
# status: active
# --- /L9_META ---
"""Shared types for the L9 Constellation Runtime v1.0.0.

In addition to the legacy dataclasses (``PacketEnvelope``, ``TraceEntry``)
that continue to drive the inflate/deflate path, this module owns the
canonical Pydantic shape of the ``tenant_context`` block as declared in
``contracts/governance/tenant_context.contract.yaml``.

The Pydantic ``TenantContext`` is the request-scoped, immutable carrier of
tenant identity for every packet. Field names match the contract YAML
verbatim (snake_case; no aliases). See ADR-0003.
"""
import uuid, time, re, hashlib, json, copy
from dataclasses import dataclass, field
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

def _uid() -> str:
    return str(uuid.uuid4())

def _now_ms() -> float:
    return time.time() * 1000

@dataclass
class TraceEntry:
    node: str
    action: str
    status: str
    timestamp: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> dict:
        d = {"node": self.node, "action": self.action, "status": self.status}
        if self.timestamp is not None:
            d["timestamp"] = self.timestamp
        if self.latency_ms is not None:
            d["latency_ms"] = self.latency_ms
        return d

@dataclass
class PacketEnvelope:
    packet_id: str
    domain: str
    action: str
    payload: dict
    trace: list
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[dict] = None
    tenant: Optional[dict] = None
    permissions: Optional[list] = None
    content_hash: Optional[str] = None

    def compute_hash(self):
        raw = json.dumps({"domain": self.domain, "action": self.action,
                          "payload": self.payload}, sort_keys=True)
        self.content_hash = hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = {"packet_id": self.packet_id, "domain": self.domain,
             "action": self.action, "payload": self.payload,
             "trace": [t.to_dict() if isinstance(t, TraceEntry) else t for t in self.trace]}
        for k in ("trace_id","correlation_id","metadata","tenant","permissions","content_hash"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d

def normalize_packet(request: dict) -> PacketEnvelope:
    pkt = PacketEnvelope(
        packet_id=request.get("packet_id", _uid()),
        domain=request["domain"],
        action=request["action"],
        payload=request.get("payload", {}),
        trace=list(request.get("trace", [])),
        trace_id=request.get("trace_id", _uid()),
        correlation_id=request.get("correlation_id"),
        metadata=request.get("metadata"),
        tenant=request.get("tenant"),
        permissions=request.get("permissions"),
    )
    pkt.compute_hash()
    return pkt

class TerminalResult:
    """Wraps a final result returned by a node handler."""
    def __init__(self, data: dict, status: str = "success"):
        self.data = data
        self.status = status

class ConstellationError(Exception):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Pydantic surface for tenant_context — see ADR-0003
# ---------------------------------------------------------------------------


class DelegationGrant(BaseModel):
    """One link in a delegation chain.

    Mirrors ``contracts/governance/delegation_chain.contract.yaml``. Frozen so
    no handler can mutate an inbound chain mid-request.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    delegator: str
    delegatee: str
    scope: str
    expires_at: Optional[str] = None


class TenantContext(BaseModel):
    """Canonical Python shape of the ``tenant_context`` block.

    Source of truth: ``contracts/governance/tenant_context.contract.yaml``.
    Frozen: a request-scoped instance must never be mutated in place.
    Field names match the contract YAML verbatim; no ``Field(alias=...)``
    is used anywhere on this surface (kernel-3 contract 1).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Required by contract
    actor: str
    on_behalf_of: str
    originator: str
    org_id: str

    # Optional by contract
    user_id: Optional[str] = None

    # principal_id: optional during R0–R2, becomes required at R3 (ADR-0003).
    principal_id: Optional[str] = None

    # Delegation chain — empty means "actor acts directly".
    delegation_chain: List[DelegationGrant] = Field(default_factory=list)

    def with_principal_id(self, principal_id: str) -> "TenantContext":
        """Return a new immutable instance with the supplied principal_id.

        Models are frozen, so mutation goes through ``model_copy``. Used by
        ``chassis.middleware.principal.principal_middleware``.
        """
        return self.model_copy(update={"principal_id": principal_id})

    def to_dict(self) -> dict:
        """Stable dict shape for the dataclass-side bridge.

        Maintains snake_case keys identical to the contract YAML. Used by
        the inflate/deflate bridge in ``chassis/contract_enforcement.py`` to
        round-trip into the legacy ``PacketEnvelope.tenant`` dict carrier
        during the R0–R2 dual-surface window (ADR-0003).
        """
        return self.model_dump(mode="python", exclude_none=False)

    @classmethod
    def from_dict(cls, payload: dict) -> "TenantContext":
        """Lift a dict (e.g. ``PacketEnvelope.tenant``) into the typed model.

        Drops unknown keys to stay forward-compatible with packets emitted by
        future R3+ chassis releases.
        """
        if not isinstance(payload, dict):
            raise ValueError(
                f"TenantContext.from_dict expects a dict, got {type(payload).__name__}"
            )
        known = {
            "actor", "on_behalf_of", "originator", "org_id", "user_id",
            "principal_id", "delegation_chain",
        }
        clean = {k: v for k, v in payload.items() if k in known}
        return cls.model_validate(clean)
