"""Spec-driven configuration loader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger(__name__)


class SpecLoader:
    def __init__(self, spec_path: str = "spec.yaml") -> None:
        self._spec_path = spec_path
        self._data: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        path = Path(self._spec_path)
        if not path.exists():
            raise FileNotFoundError(f"spec.yaml not found at {self._spec_path}")
        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        self._data = cast(dict[str, Any], loaded)
        logger.info("Spec loaded", extra={"path": self._spec_path})
        return self._data

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def get_actions(self) -> list[str]:
        engine = cast(dict[str, Any], self._data.get("l9", {}).get("engine", {}))
        return cast(list[str], engine.get("actions", []))

    def get_node_name(self) -> str:
        node = cast(dict[str, Any], self._data.get("l9", {}).get("node", {}))
        return cast(str, node.get("name", "unknown"))
