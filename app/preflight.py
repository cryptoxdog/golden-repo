from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path

from app.config import AppConfig, get_config

logger = logging.getLogger(__name__)


class PreflightError(Exception):
    pass


def run_preflight(cfg: AppConfig | None = None) -> None:
    if cfg is None:
        cfg = get_config()

    _validate_env_keys(cfg)
    _validate_app_module(cfg.app_module)
    _validate_state_directory(cfg)
    _validate_contracts_directory()
    _validate_signing_key(cfg)

    logger.info("preflight_passed", extra={"service": cfg.service_name, "env": cfg.environment})


def _validate_env_keys(cfg: AppConfig) -> None:
    required_keys = [
        "L9_ENVIRONMENT",
        "L9_NODE_NAME",
        "L9_SERVICE_NAME",
        "L9_STATE_DB_PATH",
        "L9_APP_MODULE",
    ]
    missing = [k for k in required_keys if not os.environ.get(k)]
    if missing:
        logger.warning(
            "preflight_env_keys_missing_using_defaults",
            extra={"missing": missing},
        )


def _validate_app_module(app_module: str) -> None:
    module_path, _, _ = app_module.partition(":")
    try:
        importlib.import_module(module_path)
    except ImportError as exc:
        raise PreflightError(f"app_module '{app_module}' is not importable: {exc}") from exc


def _validate_state_directory(cfg: AppConfig) -> None:
    db_path = Path(cfg.state_db_path)
    parent = db_path.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PreflightError(f"Cannot create state directory '{parent}': {exc}") from exc
    test_file = parent / ".l9_write_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
    except OSError as exc:
        raise PreflightError(f"State directory '{parent}' is not writable: {exc}") from exc


def _validate_contracts_directory() -> None:
    contracts_dir = Path("contracts")
    if not contracts_dir.exists():
        raise PreflightError("contracts/ directory is absent — required contract YAML files missing")
    required = ["packet_envelope_v1.yaml", "conformant_node_contract.yaml"]
    missing = [f for f in required if not (contracts_dir / f).exists()]
    if missing:
        raise PreflightError(f"Required contract files missing: {missing}")


def _validate_signing_key(cfg: AppConfig) -> None:
    if cfg.require_signature:
        if not cfg.signing_private_key:
            raise PreflightError(
                "L9_REQUIRE_SIGNATURE=true but L9_SIGNING_PRIVATE_KEY is not set"
            )
        if len(cfg.signing_private_key) < 32:
            raise PreflightError(
                "L9_SIGNING_PRIVATE_KEY is suspiciously short (< 32 chars) — verify key material"
            )
