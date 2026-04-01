from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DEDUP_WINDOW_SECONDS = 86400


class DuplicatePacketError(Exception):
    def __init__(self, idempotency_key: str, tenant_org_id: str, first_seen_at: str) -> None:
        self.idempotency_key = idempotency_key
        self.tenant_org_id = tenant_org_id
        self.first_seen_at = first_seen_at
        super().__init__(
            f"Duplicate packet: idempotency_key={idempotency_key!r} "
            f"tenant={tenant_org_id!r} first_seen={first_seen_at}"
        )


class IdempotencyStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_table()

    def _ensure_table(self) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS packet_receipts (
                idempotency_key TEXT NOT NULL,
                tenant_org_id   TEXT NOT NULL,
                packet_id       TEXT NOT NULL,
                source_node     TEXT NOT NULL,
                first_seen_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                PRIMARY KEY (idempotency_key, tenant_org_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_receipts_seen ON packet_receipts(first_seen_at)"
        )
        self._conn.commit()

    def check_and_record(
        self,
        *,
        idempotency_key: str,
        tenant_org_id: str,
        packet_id: str,
        source_node: str,
    ) -> None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT first_seen_at FROM packet_receipts WHERE idempotency_key=? AND tenant_org_id=?",
            (idempotency_key, tenant_org_id),
        ).fetchone()
        if row is not None:
            raise DuplicatePacketError(idempotency_key, tenant_org_id, row[0])
        self._conn.execute(
            "INSERT INTO packet_receipts (idempotency_key, tenant_org_id, packet_id, source_node) VALUES (?,?,?,?)",
            (idempotency_key, tenant_org_id, packet_id, source_node),
        )
        self._conn.commit()
        logger.debug(
            "idempotency_recorded",
            extra={"idempotency_key": idempotency_key, "tenant": tenant_org_id},
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
