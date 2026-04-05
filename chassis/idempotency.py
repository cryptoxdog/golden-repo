"""Per-tenant idempotency enforcement backed by SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class IdempotencyStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("IdempotencyStore not connected")
        return self._conn

    def check_and_store(
        self,
        *,
        idempotency_key: str,
        tenant_id: str,
        packet_id: str,
        source_node: str,
    ) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT cached_response FROM packet_receipts WHERE idempotency_key = ? AND tenant_id = ?",
            (idempotency_key, tenant_id),
        ).fetchone()
        if row is not None:
            logger.info("Idempotency hit", extra={"idempotency_key": idempotency_key, "tenant_id": tenant_id})
            return json.loads(row[0]) if row[0] else None
        conn.execute(
            "INSERT INTO packet_receipts "
            "(packet_id, idempotency_key, tenant_id, source_node, cached_response) "
            "VALUES (?, ?, ?, ?, NULL)",
            (packet_id, idempotency_key, tenant_id, source_node),
        )
        conn.commit()
        return None

    def store_response(self, *, idempotency_key: str, tenant_id: str, response: dict[str, Any]) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE packet_receipts SET cached_response = ? WHERE idempotency_key = ? AND tenant_id = ?",
            (json.dumps(response), idempotency_key, tenant_id),
        )
        conn.commit()
