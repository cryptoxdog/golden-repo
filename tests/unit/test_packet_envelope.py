from __future__ import annotations

import pytest
from pydantic import ValidationError

from chassis.types import (
    LineageSection,
    PacketEnvelope,
    PacketType,
    TenantSection,
    build_root_packet,
)


def _tenant() -> TenantSection:
    return TenantSection(
        actor="user-1",
        on_behalf_of="user-1",
        originator="api-gateway",
        org_id="org-abc",
    )


def test_build_root_packet_populates_all_required_fields() -> None:
    pkt = build_root_packet(
        source_node="gateway",
        destination_node="engine",
        action="execute",
        tenant=_tenant(),
        payload={"foo": "bar"},
    )
    assert pkt.packet_id
    assert pkt.schema_version == "1.1"
    assert pkt.idempotency_key
    assert pkt.lineage.root_id
    assert pkt.lineage.generation == 0
    assert pkt.security is not None
    assert pkt.security.content_hash
    assert pkt.security.envelope_hash


def test_content_hash_verified() -> None:
    pkt = build_root_packet(
        source_node="gateway",
        destination_node="engine",
        action="execute",
        tenant=_tenant(),
        payload={"x": 1},
    )
    assert pkt.verify_content_hash() is True


def test_derive_increments_generation() -> None:
    root = build_root_packet(
        source_node="gateway",
        destination_node="engine",
        action="execute",
        tenant=_tenant(),
        payload={},
    )
    derived = root.derive(
        action="process",
        destination_node="worker",
        payload={"step": 2},
    )
    assert derived.lineage.generation == 1
    assert derived.lineage.root_id == root.lineage.root_id
    assert derived.lineage.parent_id == root.packet_id
    assert derived.tenant.org_id == root.tenant.org_id


def test_derive_preserves_tenant_immutability() -> None:
    root = build_root_packet(
        source_node="a", destination_node="b", action="x",
        tenant=_tenant(), payload={},
    )
    derived = root.derive(action="y", destination_node="c", payload={})
    assert derived.tenant == root.tenant


def test_schema_version_must_be_1_1() -> None:
    with pytest.raises(ValidationError):
        PacketEnvelope(
            schema_version="2.0",
            source_node="a",
            destination_node="b",
            action="x",
            tenant=_tenant(),
            payload={},
            lineage=LineageSection(root_id="r", generation=0),
        )


def test_tenant_fields_required() -> None:
    with pytest.raises(ValidationError):
        TenantSection(actor="", on_behalf_of="x", originator="x", org_id="x")


def test_append_trace() -> None:
    pkt = build_root_packet(
        source_node="a", destination_node="b", action="x",
        tenant=_tenant(), payload={},
    )
    pkt.append_trace("b", "x", duration_ms=12.5)
    assert len(pkt.trace) == 1
    assert pkt.trace[0].node == "b"
    assert pkt.trace[0].duration_ms == 12.5


def test_packet_type_enum_values() -> None:
    pkt = build_root_packet(
        source_node="a", destination_node="b", action="describe",
        tenant=_tenant(), payload={},
        packet_type=PacketType.describe,
    )
    assert pkt.packet_type == PacketType.describe
