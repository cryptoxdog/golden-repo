"""Idempotent SQLite schema application."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS packet_receipts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 packet_id TEXT NOT NULL,
 idempotency_key TEXT NOT NULL,
 tenant_id TEXT NOT NULL,
 source_node TEXT NOT NULL,
 cached_response TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
 UNIQUE (idempotency_key, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_receipts_tenant
 ON packet_receipts (tenant_id);

CREATE INDEX IF NOT EXISTS idx_receipts_idempotency
 ON packet_receipts (idempotency_key, tenant_id);

CREATE TRIGGER IF NOT EXISTS trg_receipts_updated_at
 AFTER UPDATE ON packet_receipts
 FOR EACH ROW
 BEGIN
 UPDATE packet_receipts
 SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
 WHERE id = OLD.id;
 END;
"""


def apply_schema(db_path: str) -> None:
    logger.info("Applying database schema", extra={"db_path": db_path})
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_SQL)
    conn.close()
    logger.info("Database schema applied successfully")
