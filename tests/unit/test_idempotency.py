from __future__ import annotations

import pytest
from chassis.idempotency import DuplicatePacketError, IdempotencyStore


@pytest.fixture
def store(tmp_path):
    s = IdempotencyStore(tmp_path / "test.db")
    s.connect()
    yield s
    s.close()


def test_first_packet_accepted(store):
    store.check_and_record(
        idempotency_key="key-1",
        tenant_org_id="org-a",
        packet_id="pkt-1",
        source_node="gateway",
    )


def test_duplicate_packet_rejected(store):
    store.check_and_record(
        idempotency_key="key-1",
        tenant_org_id="org-a",
        packet_id="pkt-1",
        source_node="gateway",
    )
    with pytest.raises(DuplicatePacketError) as exc_info:
        store.check_and_record(
            idempotency_key="key-1",
            tenant_org_id="org-a",
            packet_id="pkt-2",
            source_node="gateway",
        )
    assert exc_info.value.idempotency_key == "key-1"


def test_same_key_different_tenant_accepted(store):
    store.check_and_record(
        idempotency_key="key-1",
        tenant_org_id="org-a",
        packet_id="pkt-1",
        source_node="gateway",
    )
    store.check_and_record(
        idempotency_key="key-1",
        tenant_org_id="org-b",
        packet_id="pkt-2",
        source_node="gateway",
    )


def test_table_created_on_connect(tmp_path):
    s = IdempotencyStore(tmp_path / "new.db")
    s.connect()
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "new.db"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "packet_receipts" in tables
    conn.close()
    s.close()
