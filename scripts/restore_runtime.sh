#!/usr/bin/env bash
set -euo pipefail
SRC="$1"
DB_PATH="${L9_STATE_DB_PATH:-/var/lib/l9/l9_state.db}"
cp "$SRC" "$DB_PATH"
