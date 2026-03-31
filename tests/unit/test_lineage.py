from __future__ import annotations

from chassis.types import TenantSection, build_root_packet


def _t():
    return TenantSection(actor="u", on_behalf_of="u", originator="gw", org_id="org")


def test_lineage_generation_increments_across_hops():
    root = build_root_packet(source_node="a", destination_node="b", action="x", tenant=_t(), payload={})
    hop1 = root.derive(action="y", destination_node="c", payload={})
    hop2 = hop1.derive(action="z", destination_node="d", payload={})

    assert root.lineage.generation == 0
    assert hop1.lineage.generation == 1
    assert hop2.lineage.generation == 2


def test_root_id_constant_across_chain():
    root = build_root_packet(source_node="a", destination_node="b", action="x", tenant=_t(), payload={})
    hop1 = root.derive(action="y", destination_node="c", payload={})
    hop2 = hop1.derive(action="z", destination_node="d", payload={})

    assert hop1.lineage.root_id == root.lineage.root_id
    assert hop2.lineage.root_id == root.lineage.root_id


def test_parent_id_chain_is_correct():
    root = build_root_packet(source_node="a", destination_node="b", action="x", tenant=_t(), payload={})
    hop1 = root.derive(action="y", destination_node="c", payload={})
    hop2 = hop1.derive(action="z", destination_node="d", payload={})

    assert hop1.lineage.parent_id == root.packet_id
    assert hop2.lineage.parent_id == hop1.packet_id


def test_correlation_id_preserved():
    root = build_root_packet(source_node="a", destination_node="b", action="x", tenant=_t(), payload={})
    hop1 = root.derive(action="y", destination_node="c", payload={})
    assert hop1.correlation_id == root.correlation_id
