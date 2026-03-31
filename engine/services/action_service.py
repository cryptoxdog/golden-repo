from __future__ import annotations

import logging
from typing import Any

import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class ActionNotFoundError(Exception):
    pass


class ActionService:
    def __init__(self, spec_path: str | Path) -> None:
        self._spec_path = Path(spec_path)
        self._spec: dict[str, Any] = {}
        self._load_spec()

    def _load_spec(self) -> None:
        if self._spec_path.exists():
            with self._spec_path.open() as fh:
                self._spec = yaml.safe_load(fh) or {}
            logger.info("action_spec_loaded", extra={"path": str(self._spec_path)})
        else:
            logger.warning("spec_not_found", extra={"path": str(self._spec_path)})
            self._spec = {}

    def get_allowed_actions(self) -> list[str]:
        return self._spec.get("allowed_actions", [])

    async def execute_action(
        self, action_name: str, parameters: dict[str, Any], tenant: str
    ) -> dict[str, Any]:
        allowed = self.get_allowed_actions()
        if allowed and action_name not in allowed:
            raise ActionNotFoundError(
                f"Action '{action_name}' not in allowed_actions for tenant '{tenant}'"
            )
        logger.info(
            "action_executing",
            extra={"action": action_name, "tenant": tenant},
        )
        return {"action": action_name, "tenant": tenant, "parameters": parameters, "status": "executed"}

    async def describe(self, tenant: str) -> dict[str, Any]:
        return {
            "service": self._spec.get("service_name", "l9-engine"),
            "version": self._spec.get("version", "0.0.0"),
            "allowed_actions": self.get_allowed_actions(),
            "tenant": tenant,
        }
