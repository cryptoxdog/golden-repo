from __future__ import annotations
import pytest
from chassis.types import normalize_packet
from chassis.contract_enforcement import enforce_packet_contract, assert_contract


def _valid():
    return normalize_packet({
        "tenant_id": "t1",
        "idempotency_key": "k1",
        "source_node": "s", "target_node": "e",
        "schema_version": "1.1", "packet_type": "REQUEST",
        "payload": {"x": 1},
        "tenant": {"actor": "a", "on_behalf_of": "b", "originator": "c", "org_id": "o1"},
    })


def test_valid_packet_no_violations():
    pkt = _valid()
    assert enforce_packet_contract(pkt) == []


def test_missing_content_hash_violation():
    pkt = _valid()
    pkt.security.content_hash = ""
    violations = enforce_packet_contract(pkt)
    assert any("content_hash" in v for v in violations)


def test_assert_contract_raises_on_violation():
    pkt = _valid()
    pkt.security.content_hash = ""
    with pytest.raises(ValueError):
        assert_contract(pkt)
