from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: str
    runtime_mode: str
    node_name: str
    service_name: str
    service_version: str
    dev_mode: bool = False
    require_signature: bool = False
    enable_metrics: bool = False
    signing_algorithm: str = "ed25519"
    signing_private_key: str | None = None
    signing_key: str | None = None
    signing_key_id: str = ""
    verifying_keys: dict[str, str] = Field(default_factory=dict)
    allowed_actions: tuple[str, ...]
    allowed_packet_types: tuple[str, ...]
    require_idempotency_for_actions: tuple[str, ...] = ()
    state_db_path: str
    app_module: str

    @model_validator(mode="after")
    def _validate(self) -> "AppConfig":
        if self.environment in {"staging", "prod"} and self.dev_mode:
            raise ValueError("dev_mode cannot be enabled in staging or prod")
        if self.runtime_mode != "single-node":
            raise ValueError("golden template supports single-node runtime mode only")
        if self.require_signature:
            if self.signing_algorithm == "ed25519":
                if not self.signing_private_key:
                    raise ValueError("ed25519 requires signing private key")
                if self.signing_key_id not in self.verifying_keys:
                    raise ValueError("verifying keys must include signing_key_id")
            elif self.signing_algorithm == "hmac-sha256":
                if not self.signing_key:
                    raise ValueError("hmac-sha256 requires signing key")
        missing = set(self.require_idempotency_for_actions) - set(self.allowed_actions)
        if missing:
            raise ValueError(f"idempotency actions missing from allowed_actions: {sorted(missing)}")
        return self

    def ensure_directories(self) -> None:
        Path(self.state_db_path).parent.mkdir(parents=True, exist_ok=True)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_tuple(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(x.strip() for x in raw.split(",") if x.strip())


def _env_json(name: str) -> dict[str, str]:
    raw = os.getenv(name, "{}")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


@lru_cache
def get_config() -> AppConfig:
    cfg = AppConfig(
        environment=os.getenv("L9_ENVIRONMENT", "prod"),
        runtime_mode=os.getenv("L9_RUNTIME_MODE", "single-node"),
        node_name=os.getenv("L9_NODE_NAME", "service-template"),
        service_name=os.getenv("L9_SERVICE_NAME", "service-template"),
        service_version=os.getenv("L9_SERVICE_VERSION", "1.0.0"),
        dev_mode=_env_bool("L9_DEV_MODE", False),
        require_signature=_env_bool("L9_REQUIRE_SIGNATURE", True),
        enable_metrics=_env_bool("L9_ENABLE_METRICS", False),
        signing_algorithm=os.getenv("L9_SIGNING_ALGORITHM", "ed25519"),
        signing_private_key=os.getenv("L9_SIGNING_PRIVATE_KEY"),
        signing_key=os.getenv("L9_SIGNING_KEY") or os.getenv("L9_SIGNING_SECRET"),
        signing_key_id=os.getenv("L9_SIGNING_KEY_ID", ""),
        verifying_keys=_env_json("L9_VERIFYING_KEYS_JSON"),
        allowed_actions=_env_tuple("L9_ALLOWED_ACTIONS"),
        allowed_packet_types=_env_tuple("L9_ALLOWED_PACKET_TYPES"),
        require_idempotency_for_actions=_env_tuple("L9_REQUIRE_IDEMPOTENCY_FOR_ACTIONS"),
        state_db_path=os.getenv("L9_STATE_DB_PATH", "/var/lib/l9/l9_state.db"),
        app_module=os.getenv("APP_MODULE", "generated_service.app:app"),
    )
    cfg.ensure_directories()
    return cfg
