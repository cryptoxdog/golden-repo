from __future__ import annotations

import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

from chassis.idempotency import IdempotencyStore
from database.init_db import apply_schema


@pytest.fixture()
def store(tmp_path: Path) -> Generator[IdempotencyStore, None, None]:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    store = IdempotencyStore(str(db_path))
    store.connect()
    try:
        yield store
    finally:
        store.close()


def test_first_check_and_store_returns_none(store: IdempotencyStore) -> None:
    result = store.check_and_store(
        idempotency_key="k1",
        tenant_id="tenant-a",
        packet_id=str(uuid.uuid4()),
        source_node="alpha",
    )
    assert result is None


def test_cached_response_round_trip(store: IdempotencyStore) -> None:
    store.check_and_store(idempotency_key="k1", tenant_id="tenant-a", packet_id="p1", source_node="alpha")
    store.store_response(idempotency_key="k1", tenant_id="tenant-a", response={"status": "success"})
    cached = store.check_and_store(idempotency_key="k1", tenant_id="tenant-a", packet_id="p2", source_node="beta")
    assert cached == {"status": "success"}


def test_same_key_allowed_for_different_tenants(store: IdempotencyStore) -> None:
    first = store.check_and_store(idempotency_key="shared", tenant_id="tenant-a", packet_id="p1", source_node="a")
    second = store.check_and_store(idempotency_key="shared", tenant_id="tenant-b", packet_id="p2", source_node="b")
    assert first is None
    assert second is None


def test_check_without_connect_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    store = IdempotencyStore(str(db_path))
    with pytest.raises(RuntimeError):
        store.check_and_store(idempotency_key="k1", tenant_id="tenant", packet_id="p1", source_node="a")
