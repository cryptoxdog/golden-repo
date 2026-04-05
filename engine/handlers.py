"""L9 engine action handlers — async handlers with payload validation."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from chassis.actions import register_handlers
from engine.services.action_service import ActionService

logger = logging.getLogger(__name__)

_service: ActionService | None = None


class ExecutePayload(BaseModel):
    action_name: str | None = None
    action: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


class DescribePayload(BaseModel):
    action_name: str = "describe"


def init_service(*, allowed_actions: list[str]) -> None:
    global _service
    _service = ActionService(allowed_actions=allowed_actions)
    logger.info("ActionService initialized", extra={"allowed_actions": allowed_actions})


def _get_service() -> ActionService:
    if _service is None:
        raise RuntimeError("ActionService not initialized — call init_service() first")
    return _service


async def handle_execute(tenant: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = ExecutePayload.model_validate(payload)
    service = _get_service()
    action_name = request.action_name or request.action or "execute"
    parameters = request.parameters or request.data
    return service.execute_action(action_name, parameters, tenant=tenant)


async def handle_describe(tenant: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = DescribePayload.model_validate(payload)
    service = _get_service()
    return service.describe_action(request.action_name, tenant=tenant)


def register_all() -> None:
    register_handlers({"execute": handle_execute, "describe": handle_describe})
    logger.info("All engine handlers registered")
