from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IdempotencyStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS packet_receipts (
                idempotency_key TEXT NOT NULL,
                tenant_id       TEXT NOT NULL,
                packet_id       TEXT NOT NULL,
                source_node     TEXT NOT NULL,
                first_seen_at   TEXT NOT NULL DEFAULT (datetime('now')),
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (idempotency_key, tenant_id)
            )
        """)
        self._conn.commit()

    def is_duplicate(self, idempotency_key: str, tenant_id: str) -> bool:
        if self._conn is None:
            raise RuntimeError("IdempotencyStore.init() not called")
        cur = self._conn.execute(
            "SELECT 1 FROM packet_receipts WHERE idempotency_key=? AND tenant_id=?",
            (idempotency_key, tenant_id),
        )
        return cur.fetchone() is not None

    def record(self, idempotency_key: str, tenant_id: str, packet_id: str, source_node: str) -> None:
        if self._conn is None:
            raise RuntimeError("IdempotencyStore.init() not called")
        self._conn.execute(
            "INSERT OR IGNORE INTO packet_receipts (idempotency_key, tenant_id, packet_id, source_node) VALUES (?,?,?,?)",
            (idempotency_key, tenant_id, packet_id, source_node),
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
