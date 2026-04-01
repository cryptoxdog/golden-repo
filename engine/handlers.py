from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from engine.services.action_service import ActionService, ActionNotFoundError

logger = logging.getLogger(__name__)

_service: ActionService | None = None


def init_service(service: ActionService) -> None:
    global _service
    _service = service
    logger.info("action_service_registered")


def _get_service() -> ActionService:
    if _service is None:
        raise RuntimeError("ActionService not initialised — call init_service() at startup")
    return _service


class ExecutePayload(BaseModel):
    action_name: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


async def handle_execute(tenant: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        validated = ExecutePayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid execute payload: {exc}") from exc

    svc = _get_service()
    try:
        return await svc.execute_action(validated.action_name, validated.parameters, tenant)
    except ActionNotFoundError as exc:
        raise KeyError(str(exc)) from exc


async def handle_describe(tenant: str, payload: dict[str, Any]) -> dict[str, Any]:
    svc = _get_service()
    return await svc.describe(tenant)


def register_all(service: ActionService) -> None:
    from chassis.actions import register_handlers
    init_service(service)
    register_handlers(
        {
            "execute": handle_execute,
            "describe": handle_describe,
        }
    )
    logger.info("all_handlers_registered")
