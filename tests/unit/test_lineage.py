from __future__ import annotations
from chassis.types import normalize_packet


def _base():
    return normalize_packet({
        "tenant_id": "t1", "idempotency_key": "k1",
        "source_node": "s", "target_node": "e",
        "schema_version": "1.1", "packet_type": "REQUEST", "payload": {},
        "tenant": {"actor": "a", "on_behalf_of": "b", "originator": "c", "org_id": "o1"},
    })


def test_root_id_constant_across_hops():
    p = _base()
    c1 = p.derive("hop1", {})
    c2 = c1.derive("hop2", {})
    assert c1.lineage.root_id == p.lineage.root_id
    assert c2.lineage.root_id == p.lineage.root_id


def test_generation_increments():
    p = _base()
    c1 = p.derive("hop1", {})
    c2 = c1.derive("hop2", {})
    assert c1.lineage.generation == p.lineage.generation + 1
    assert c2.lineage.generation == p.lineage.generation + 2


def test_parent_id_points_to_parent():
    p = _base()
    c = p.derive("hop1", {})
    assert c.lineage.parent_id == p.packet_id


def test_correlation_id_preserved():
    p = _base()
    c = p.derive("hop1", {})
    assert c.correlation_id == p.correlation_id
