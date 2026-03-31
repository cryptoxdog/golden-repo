from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from database.init_db import apply_schema


def test_schema_creates_packet_receipts(tmp_path):
    db = tmp_path / "test.db"
    apply_schema(db)
    conn = sqlite3.connect(str(db))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "packet_receipts" in tables
    assert "audit_events" in tables
    conn.close()


def test_schema_is_idempotent(tmp_path):
    db = tmp_path / "idem.db"
    apply_schema(db)
    apply_schema(db)


def test_packet_receipts_columns(tmp_path):
    db = tmp_path / "cols.db"
    apply_schema(db)
    conn = sqlite3.connect(str(db))
    cols = {row[1] for row in conn.execute("PRAGMA table_info(packet_receipts)").fetchall()}
    assert "idempotency_key" in cols
    assert "tenant_org_id" in cols
    assert "packet_id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    conn.close()
