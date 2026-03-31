#!/usr/bin/env bash
set -euo pipefail
APP_MODULE="${APP_MODULE:-generated_service.app:app}"
python scripts/predeploy_check.py
exec uvicorn "$APP_MODULE" --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --log-level "${LOG_LEVEL:-info}"
