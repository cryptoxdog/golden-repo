from __future__ import annotations

from importlib import import_module
from pathlib import Path
import tempfile

from app.config import AppConfig


class PreflightFailure(RuntimeError):
    pass


def run_preflight(config: AppConfig) -> None:
    _validate_app_module(config.app_module)
    _validate_state_directory(config)


def _validate_app_module(app_module: str) -> None:
    module_name, sep, attr_name = app_module.partition(":")
    if not sep:
        raise PreflightFailure("APP_MODULE must be in module:attribute format")
    module = import_module(module_name)
    if not hasattr(module, attr_name):
        raise PreflightFailure(f"APP_MODULE attribute missing: {app_module}")
    app_obj = getattr(module, attr_name)
    if not hasattr(app_obj, "__call__"):
        raise PreflightFailure("APP_MODULE object is not callable")


def _validate_state_directory(config: AppConfig) -> None:
    parent = Path(config.state_db_path).parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=parent, prefix=".l9test_", delete=True) as f:
        f.write(b"ok")
        f.flush()
