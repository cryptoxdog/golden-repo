from __future__ import annotations
import pytest
from chassis.types import PacketEnvelope, TenantContext, LineageInfo, SecurityInfo, GovernanceInfo, normalize_packet


def _valid_raw(**overrides):
    base = {
        "packet_id": "pkt-001",
        "tenant_id": "tenant-a",
        "correlation_id": "corr-001",
        "idempotency_key": "idem-001",
        "source_node": "ingress",
        "target_node": "engine",
        "schema_version": "1.1",
        "packet_type": "REQUEST",
        "payload": {"action_name": "execute"},
        "tenant": {"actor": "user1", "on_behalf_of": "org1", "originator": "api", "org_id": "org-001"},
    }
    base.update(overrides)
    return base


def test_normalize_valid():
    pkt = normalize_packet(_valid_raw())
    assert pkt.packet_id == "pkt-001"
    assert pkt.security.content_hash != ""
    assert pkt.security.envelope_hash != ""


def test_schema_version_enforced():
    with pytest.raises(ValueError, match="schema_version"):
        normalize_packet(_valid_raw(schema_version="2.0"))


def test_missing_tenant_actor():
    raw = _valid_raw()
    raw["tenant"]["actor"] = ""
    with pytest.raises(ValueError, match="actor"):
        normalize_packet(raw)


def test_compute_hash_sets_both_hashes():
    pkt = normalize_packet(_valid_raw())
    assert len(pkt.security.content_hash) == 64
    assert len(pkt.security.envelope_hash) == 64


def test_derive_increments_generation():
    pkt = normalize_packet(_valid_raw())
    child = pkt.derive("worker", {"action_name": "describe"})
    assert child.lineage.generation == pkt.lineage.generation + 1
    assert child.lineage.root_id == pkt.lineage.root_id
    assert child.lineage.parent_id == pkt.packet_id


def test_derive_preserves_tenant_id():
    pkt = normalize_packet(_valid_raw())
    child = pkt.derive("worker", {})
    assert child.tenant_id == pkt.tenant_id


def test_append_trace():
    pkt = normalize_packet(_valid_raw())
    pkt.append_trace("router", "entry")
    assert len(pkt.trace) == 1
    assert pkt.trace[0].node == "router"


def test_missing_idempotency_key_raises():
    with pytest.raises(ValueError, match="idempotency_key"):
        normalize_packet(_valid_raw(idempotency_key=""))
