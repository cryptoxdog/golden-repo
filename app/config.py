"""Application configuration with full L9_* key coverage."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    environment: str = ""
    node_name: str = ""
    service_name: str = ""
    service_version: str = "0.1.0"
    runtime_mode: str = "standalone"
    allowed_actions: list[str] = field(default_factory=list)
    state_db_path: str = "./state.db"
    require_signature: bool = False
    signing_secret: str = ""
    signing_algorithm: str = "hmac-sha256"
    json_logs: bool = True
    log_level: str = "INFO"
    max_packet_bytes: int = 1048576
    max_hop_depth: int = 16
    allowed_clock_skew_seconds: int = 30
    contracts_dir: str = "./contracts"
    app_module: str = "engine.main:app"


def load_config() -> AppConfig:
    actions_raw = os.environ.get("L9_ALLOWED_ACTIONS", "execute,describe")
    actions = [action.strip() for action in actions_raw.split(",") if action.strip()]
    config = AppConfig(
        environment=os.environ.get("L9_ENVIRONMENT", "development"),
        node_name=os.environ.get("L9_NODE_NAME", "unknown"),
        service_name=os.environ.get("L9_SERVICE_NAME", "l9-engine"),
        service_version=os.environ.get("L9_SERVICE_VERSION", "0.1.0"),
        runtime_mode=os.environ.get("L9_RUNTIME_MODE", "standalone"),
        allowed_actions=actions,
        state_db_path=os.environ.get("L9_STATE_DB_PATH", "./state.db"),
        require_signature=os.environ.get("L9_REQUIRE_SIGNATURE", "false").lower() == "true",
        signing_secret=os.environ.get("L9_SIGNING_SECRET", ""),
        signing_algorithm=os.environ.get("L9_SIGNING_ALGORITHM", "hmac-sha256"),
        json_logs=os.environ.get("L9_JSON_LOGS", "true").lower() == "true",
        log_level=os.environ.get("L9_LOG_LEVEL", "INFO"),
        max_packet_bytes=int(os.environ.get("L9_MAX_PACKET_BYTES", "1048576")),
        max_hop_depth=int(os.environ.get("L9_MAX_HOP_DEPTH", "16")),
        allowed_clock_skew_seconds=int(os.environ.get("L9_ALLOWED_CLOCK_SKEW_SECONDS", "30")),
        contracts_dir=os.environ.get("L9_CONTRACTS_DIR", "./contracts"),
        app_module=os.environ.get("APP_MODULE", "engine.main:app"),
    )
    logger.info("Config loaded", extra={"environment": config.environment, "node": config.node_name})
    return config
