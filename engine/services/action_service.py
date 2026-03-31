from __future__ import annotations

from engine.config.loader import SpecLoader
from engine.core.result import ActionResult


class ActionService:
    def __init__(self, spec_loader: SpecLoader | None = None) -> None:
        self._spec_loader = spec_loader or SpecLoader()

    def execute_action(self, action_name: str, parameters: dict) -> dict:
        allowed_actions = set(self._spec_loader.action_names())
        accepted = action_name in allowed_actions
        result = ActionResult(
            accepted=accepted,
            action_name=action_name,
            parameters=parameters,
        )
        return result.to_dict()

    def describe(self) -> dict:
        spec = self._spec_loader.load()
        return {
            "service": spec.service.name,
            "actions": [action.name for action in spec.actions],
        }
