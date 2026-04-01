from __future__ import annotations

import pytest
from chassis.idempotency import DuplicatePacketError, IdempotencyStore
from chassis.types import TenantSection, build_root_packet


def test_cross_tenant_idempotency_keys_are_isolated(tmp_path):
    store = IdempotencyStore(tmp_path / "iso.db")
    store.connect()

    store.check_and_record(
        idempotency_key="shared-key",
        tenant_org_id="org-A",
        packet_id="pkt-a",
        source_node="gw",
    )
    store.check_and_record(
        idempotency_key="shared-key",
        tenant_org_id="org-B",
        packet_id="pkt-b",
        source_node="gw",
    )
    store.close()


def test_duplicate_within_same_tenant_blocked(tmp_path):
    store = IdempotencyStore(tmp_path / "dup.db")
    store.connect()

    store.check_and_record(
        idempotency_key="key-x",
        tenant_org_id="org-C",
        packet_id="pkt-1",
        source_node="gw",
    )
    with pytest.raises(DuplicatePacketError):
        store.check_and_record(
            idempotency_key="key-x",
            tenant_org_id="org-C",
            packet_id="pkt-2",
            source_node="gw",
        )
    store.close()


def test_tenant_section_fields_frozen():
    t = TenantSection(actor="a", on_behalf_of="b", originator="c", org_id="d")
    with pytest.raises(Exception):
        t.actor = "tampered"  # type: ignore[misc]
