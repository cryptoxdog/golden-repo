from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from database.init_db import apply_schema


def test_apply_schema_creates_packet_receipts_table(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='packet_receipts'").fetchone()
        assert row == ("packet_receipts",)
    finally:
        conn.close()


def test_apply_schema_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    apply_schema(str(db_path))
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='packet_receipts'"
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_unique_constraint_enforced(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    apply_schema(str(db_path))
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            (
                "INSERT INTO packet_receipts "
                "(packet_id, idempotency_key, tenant_id, source_node, cached_response) "
                "VALUES (?, ?, ?, ?, ?)"
            ),
            ("p1", "dup", "tenant-a", "alpha", None),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                (
                    "INSERT INTO packet_receipts "
                    "(packet_id, idempotency_key, tenant_id, source_node, cached_response) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                ("p2", "dup", "tenant-a", "alpha", None),
            )
            conn.commit()
    finally:
        conn.close()
