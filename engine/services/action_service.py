"""Domain action execution service with tenant scoping."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ActionService:
    def __init__(self, *, allowed_actions: list[str]) -> None:
        self._allowed_actions = set(allowed_actions)

    def execute_action(self, action_name: str, parameters: dict[str, Any], *, tenant: str) -> dict[str, Any]:
        if action_name not in self._allowed_actions:
            raise ValueError(f"Action not allowed: {action_name}")
        logger.info("Executing action", extra={"action": action_name, "tenant": tenant})
        return {
            "action": action_name,
            "tenant": tenant,
            "result": "executed",
            "parameters_received": sorted(parameters.keys()),
        }

    def describe_action(self, action_name: str, *, tenant: str) -> dict[str, Any]:
        return {
            "action": action_name,
            "tenant": tenant,
            "allowed": action_name in self._allowed_actions,
            "available_actions": sorted(self._allowed_actions),
        }
