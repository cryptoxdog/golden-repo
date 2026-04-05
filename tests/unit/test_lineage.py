from __future__ import annotations

from chassis.types import PacketEnvelope, Payload, TenantInfo


def make_packet() -> PacketEnvelope:
    return PacketEnvelope(
        source_node="alpha",
        target_node="beta",
        tenant=TenantInfo(tenant_id="t1", actor="igor", originator="igor", org_id="org"),
        payload=Payload(action="execute", data={"x": 1}),
    )


def test_root_id_remains_constant_across_derivation_chain() -> None:
    root = make_packet()
    child = root.derive(new_action="describe")
    grandchild = child.derive(new_action="execute")
    assert root.lineage.root_id == child.lineage.root_id == grandchild.lineage.root_id


def test_generation_increments_by_one_on_each_hop() -> None:
    packet = make_packet()
    child = packet.derive()
    grandchild = child.derive()
    assert child.lineage.generation == packet.lineage.generation + 1
    assert grandchild.lineage.generation == child.lineage.generation + 1


def test_parent_id_chains_to_prior_packet_id() -> None:
    packet = make_packet()
    child = packet.derive()
    grandchild = child.derive()
    assert child.lineage.parent_id == packet.packet_id
    assert grandchild.lineage.parent_id == child.packet_id


def test_tenant_context_is_preserved_on_derive() -> None:
    packet = make_packet()
    child = packet.derive()
    assert child.tenant == packet.tenant
