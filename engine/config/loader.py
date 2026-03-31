from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SpecLoader:
    def __init__(self, spec_path: str | Path) -> None:
        self._spec_path = Path(spec_path)
        self._spec: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        if not self._spec_path.exists():
            raise FileNotFoundError(f"spec.yaml not found at {self._spec_path}")
        with self._spec_path.open() as fh:
            self._spec = yaml.safe_load(fh)
        logger.info("spec_loaded", extra={"path": str(self._spec_path)})
        return self._spec

    def get_allowed_actions(self) -> list[str]:
        if self._spec is None:
            self.load()
        assert self._spec is not None
        return self._spec.get("allowed_actions", [])

    def get_service_name(self) -> str:
        if self._spec is None:
            self.load()
        assert self._spec is not None
        return self._spec.get("service_name", "l9-engine")
