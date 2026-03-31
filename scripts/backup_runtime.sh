#!/usr/bin/env bash
set -euo pipefail
DB_PATH="${L9_STATE_DB_PATH:-/var/lib/l9/l9_state.db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/l9_state_$(date +%Y%m%d_%H%M%S).sqlite3"
