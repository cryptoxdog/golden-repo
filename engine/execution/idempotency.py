from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS packet_receipts (
  packet_id TEXT NOT NULL,
  source_node TEXT NOT NULL,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (packet_id, source_node)
);
"""


class IdempotencyStore:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def record_packet_receipt(self, *, packet_id: str, source_node: str) -> bool:
        cur = self._conn.cursor()
        cur.execute("INSERT OR IGNORE INTO packet_receipts (packet_id, source_node) VALUES (?, ?)", (packet_id, source_node))
        self._conn.commit()
        return cur.rowcount == 1
