from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS packet_receipts (
    idempotency_key TEXT NOT NULL,
    tenant_org_id   TEXT NOT NULL,
    packet_id       TEXT NOT NULL,
    source_node     TEXT NOT NULL,
    first_seen_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (idempotency_key, tenant_org_id)
);

CREATE INDEX IF NOT EXISTS idx_receipts_tenant ON packet_receipts(tenant_org_id);
CREATE INDEX IF NOT EXISTS idx_receipts_seen   ON packet_receipts(first_seen_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    who             TEXT NOT NULL,
    what            TEXT NOT NULL,
    tenant_org_id   TEXT NOT NULL,
    packet_id       TEXT NOT NULL,
    correlation_id  TEXT NOT NULL,
    node            TEXT NOT NULL,
    before_state    TEXT,
    after_state     TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_events(tenant_org_id);
CREATE INDEX IF NOT EXISTS idx_audit_corr   ON audit_events(correlation_id);
"""


def apply_schema(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logger.info("schema_applied", extra={"db_path": str(db_path)})
    finally:
        conn.close()
