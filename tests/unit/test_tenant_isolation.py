from __future__ import annotations
import pytest
from chassis.types import normalize_packet


def test_mismatched_tenant_rejected():
    raw = {
        "tenant_id": "tenant-a",
        "idempotency_key": "idem-1",
        "source_node": "s", "target_node": "t",
        "schema_version": "1.1", "packet_type": "REQUEST",
        "payload": {},
        "tenant": {"actor": "u", "on_behalf_of": "o", "originator": "api", "org_id": "org-1"},
    }
    pkt = normalize_packet(raw)
    assert pkt.tenant_id == "tenant-a"


def test_empty_tenant_id_rejected():
    raw = {
        "tenant_id": "",
        "idempotency_key": "idem-1",
        "source_node": "s", "target_node": "t",
        "schema_version": "1.1", "packet_type": "REQUEST",
        "payload": {},
        "tenant": {"actor": "u", "on_behalf_of": "o", "originator": "api", "org_id": "org-1"},
    }
    with pytest.raises(ValueError, match="tenant_id"):
        normalize_packet(raw)


def test_tenant_fields_immutable_in_derived():
    raw = {
        "tenant_id": "tenant-a",
        "idempotency_key": "idem-1",
        "source_node": "s", "target_node": "t",
        "schema_version": "1.1", "packet_type": "REQUEST",
        "payload": {},
        "tenant": {"actor": "u", "on_behalf_of": "o", "originator": "api", "org_id": "org-1"},
    }
    pkt = normalize_packet(raw)
    child = pkt.derive("worker", {})
    assert child.tenant.actor == pkt.tenant.actor
    assert child.tenant.org_id == pkt.tenant.org_id
