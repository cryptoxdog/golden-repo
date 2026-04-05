"""Preflight checks — gates startup on required conditions."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

from app.config import AppConfig

logger = logging.getLogger(__name__)


class PreflightError(RuntimeError):
    pass


def run_preflight(config: AppConfig) -> None:
    logger.info("Running preflight checks")
    _check_app_module(config.app_module)
    _check_state_directory(config.state_db_path)
    _check_contracts_dir(config.contracts_dir)
    _check_signing_key(config)
    _check_allowed_actions(config.allowed_actions)
    logger.info("All preflight checks passed")


def _check_app_module(app_module: str) -> None:
    module_path = app_module.split(":")[0]
    try:
        importlib.import_module(module_path)
    except ImportError as exc:  # pragma: no cover - defensive
        raise PreflightError(f"APP_MODULE not importable: {module_path} — {exc}") from exc


def _check_state_directory(db_path: str) -> None:
    parent = Path(db_path).parent
    if not parent.exists():
        raise PreflightError(f"State DB directory does not exist: {parent}")
    if not parent.is_dir():
        raise PreflightError(f"State DB parent is not a directory: {parent}")


def _check_contracts_dir(contracts_dir: str) -> None:
    path = Path(contracts_dir)
    if not path.is_dir():
        raise PreflightError(f"Contracts directory not found: {contracts_dir}")
    yamls = list(path.glob("*.yaml"))
    if not yamls:
        raise PreflightError(f"No contract YAML files in {contracts_dir}")


def _check_signing_key(config: AppConfig) -> None:
    if config.require_signature and not config.signing_secret:
        raise PreflightError("L9_REQUIRE_SIGNATURE=true but L9_SIGNING_SECRET is empty")


def _check_allowed_actions(actions: list[str]) -> None:
    if not actions:
        raise PreflightError("L9_ALLOWED_ACTIONS is empty — no actions to serve")
