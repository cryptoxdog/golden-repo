from __future__ import annotations

from pydantic import ValidationError

from chassis.types import Lineage, PacketEnvelope, Payload, TenantInfo, TraceStatus, normalize_packet


def make_packet() -> PacketEnvelope:
    return PacketEnvelope(
        source_node="alpha",
        target_node="beta",
        tenant=TenantInfo(tenant_id="t1", actor="igor", originator="igor", org_id="org"),
        payload=Payload(action="execute", data={"x": 1}),
    )


def test_packet_envelope_computes_content_hash() -> None:
    packet = make_packet()
    assert packet.security.content_hash


def test_verify_content_hash_returns_true_for_fresh_packet() -> None:
    packet = make_packet()
    assert packet.verify_content_hash() is True


def test_verify_content_hash_detects_payload_mutation() -> None:
    packet = make_packet()
    packet.payload.data["x"] = 2
    assert packet.verify_content_hash() is False


def test_normalize_packet_fills_defaults() -> None:
    packet = normalize_packet(
        {
            "source_node": "origin",
            "target_node": "self",
            "tenant": {"tenant_id": "t1", "actor": "igor", "originator": "igor", "org_id": "org"},
            "payload": {"action": "execute", "data": {"a": 1}},
        }
    )
    assert packet.packet_id
    assert packet.correlation_id
    assert packet.idempotency_key
    assert packet.payload.action == "execute"


def test_derive_increments_lineage() -> None:
    packet = make_packet()
    child = packet.derive(new_action="describe", new_target="gamma")
    assert child.lineage.root_id == packet.lineage.root_id
    assert child.lineage.parent_id == packet.packet_id
    assert child.lineage.generation == packet.lineage.generation + 1
    assert child.payload.action == "describe"
    assert child.target_node == "gamma"


def test_append_trace_adds_trace_entry() -> None:
    packet = make_packet()
    packet.append_trace(node="alpha", action="handle", status=TraceStatus.PROCESSING)
    assert len(packet.trace) == 1
    assert packet.trace[0].status == TraceStatus.PROCESSING


def test_negative_generation_rejected() -> None:
    try:
        Lineage(generation=-1)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")


def test_normalize_packet_uses_parameters_fallback() -> None:
    packet = normalize_packet(
        {
            "action": "execute",
            "parameters": {"foo": "bar"},
            "tenant": {"tenant_id": "t1", "actor": "igor", "originator": "igor", "org_id": "org"},
        }
    )
    assert packet.payload.data == {"foo": "bar"}
