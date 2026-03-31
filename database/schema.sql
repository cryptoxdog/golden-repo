CREATE TABLE IF NOT EXISTS packet_receipts (
  packet_id TEXT NOT NULL,
  source_node TEXT NOT NULL,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (packet_id, source_node)
);
