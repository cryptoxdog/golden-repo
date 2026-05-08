from __future__ import annotations

from collections.abc import Callable

from engine.compliance.prohibited_factors import contains_prohibited_factors
from engine.config.loader import SpecLoader
from engine.core.errors import EngineError
from engine.models.action_models import DescribePayload, ExecuteActionPayload
from engine.services.action_service import ActionService

Handler = Callable[[str, dict], dict]


def register_all(registrar: dict[str, Handler] | None = None) -> dict[str, Handler]:
    registry = registrar if registrar is not None else {}
    registry["execute"] = handle_execute
    registry["describe"] = handle_describe
    registry["health"] = handle_health
    return registry


async def handle_execute(tenant: str, payload: dict) -> dict:
    validated = ExecuteActionPayload.model_validate(payload)
    if contains_prohibited_factors(validated.parameters):
        raise EngineError(
            action="execute",
            tenant=tenant,
            client_message="Payload contains prohibited factors",
            detail="Prohibited keys are not permitted in execute payloads",
        )
    service = ActionService(SpecLoader())
    return await service.execute_action(validated.action_name, validated.parameters)


async def handle_describe(tenant: str, payload: dict) -> dict:
    DescribePayload.model_validate(payload)
    service = ActionService(SpecLoader())
    return await service.describe()
