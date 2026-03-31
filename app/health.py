from __future__ import annotations

import os

from app.config import get_config


def health_payload(*, adapter_ready: bool) -> dict:
    cfg = get_config()
    return {
        "status": "ok",
        "service": cfg.service_name,
        "version": cfg.service_version,
        "adapter_ready": adapter_ready,
    }


def readiness_payload() -> dict:
    return {
        "ready": True,
        "max_concurrent_executions": int(os.getenv("L9_MAX_CONCURRENT_EXECUTIONS", "100")),
        "replay_enabled": os.getenv("L9_REPLAY_ENABLED", "true").lower() == "true",
        "memory_records": 0,
    }
