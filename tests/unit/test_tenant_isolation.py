from __future__ import annotations

from pathlib import Path

import pytest

from chassis.idempotency import IdempotencyStore
from database.init_db import apply_schema
from engine.services.action_service import ActionService


def test_action_service_propagates_tenant() -> None:
    service = ActionService(allowed_actions=["execute", "describe"])
    result = service.execute_action("execute", {"foo": "bar"}, tenant="tenant-a")
    assert result["tenant"] == "tenant-a"


def test_action_service_rejects_unallowed_action() -> None:
    service = ActionService(allowed_actions=["describe"])
    with pytest.raises(ValueError):
        service.execute_action("execute", {}, tenant="tenant-a")


def test_idempotency_is_scoped_by_tenant(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    store = IdempotencyStore(str(db_path))
    store.connect()
    try:
        assert store.check_and_store(idempotency_key="dup", tenant_id="a", packet_id="p1", source_node="n1") is None
        assert store.check_and_store(idempotency_key="dup", tenant_id="b", packet_id="p2", source_node="n1") is None
    finally:
        store.close()
