from __future__ import annotations
import pytest
from chassis.idempotency import IdempotencyStore


@pytest.fixture
def store(tmp_path):
    s = IdempotencyStore(str(tmp_path / "test.db"))
    s.init()
    yield s
    s.close()


def test_not_duplicate_initially(store):
    assert store.is_duplicate("key-1", "tenant-a") is False


def test_record_then_detect(store):
    store.record("key-1", "tenant-a", "pkt-1", "ingress")
    assert store.is_duplicate("key-1", "tenant-a") is True


def test_cross_tenant_no_collision(store):
    store.record("key-1", "tenant-a", "pkt-1", "ingress")
    assert store.is_duplicate("key-1", "tenant-b") is False


def test_idempotent_record(store):
    store.record("key-1", "tenant-a", "pkt-1", "ingress")
    store.record("key-1", "tenant-a", "pkt-1", "ingress")
    assert store.is_duplicate("key-1", "tenant-a") is True
