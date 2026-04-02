from __future__ import annotations
import sqlite3
import pytest
from database.init_db import apply_schema


def test_apply_schema_creates_table(tmp_path):
    db = str(tmp_path / "test.db")
    apply_schema(db)
    conn = sqlite3.connect(db)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='packet_receipts'")
    assert cur.fetchone() is not None
    conn.close()


def test_apply_schema_idempotent(tmp_path):
    db = str(tmp_path / "test.db")
    apply_schema(db)
    apply_schema(db)
    conn = sqlite3.connect(db)
    cur = conn.execute("SELECT count(*) FROM packet_receipts")
    assert cur.fetchone()[0] == 0
    conn.close()


def test_tenant_id_column_exists(tmp_path):
    db = str(tmp_path / "test.db")
    apply_schema(db)
    conn = sqlite3.connect(db)
    cur = conn.execute("PRAGMA table_info(packet_receipts)")
    cols = [row[1] for row in cur.fetchall()]
    assert "tenant_id" in cols
    assert "idempotency_key" in cols
    assert "created_at" in cols
    conn.close()
