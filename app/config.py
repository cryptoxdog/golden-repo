from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="L9_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: str = Field(default="development")
    runtime_mode: str = Field(default="engine")
    node_name: str = Field(default="l9-node-local")
    service_name: str = Field(default="l9-engine")
    service_version: str = Field(default="0.0.0")
    require_signature: bool = Field(default=False)
    signing_private_key: str | None = Field(default=None)
    signing_algorithm: str = Field(default="hmac-sha256")
    allowed_actions: list[str] = Field(default_factory=list)
    state_db_path: str = Field(default="/tmp/l9_state.db")
    app_module: str = Field(default="engine.main:app")
    json_logs: bool = Field(default=True)
    expose_internal_errors: bool = Field(default=False)
    max_packet_bytes: int = Field(default=1_048_576)
    max_hop_depth: int = Field(default=10)
    max_concurrent_executions: int = Field(default=100)
    replay_enabled: bool = Field(default=True)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_signing(self) -> "AppConfig":
        if self.require_signature and not self.signing_private_key:
            raise ValueError(
                "L9_SIGNING_PRIVATE_KEY must be set when L9_REQUIRE_SIGNATURE=true"
            )
        return self


@functools.lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
