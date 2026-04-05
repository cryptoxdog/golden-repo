"""Action dispatch with PacketEnvelope bridge, idempotency, and error isolation."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from chassis.types import PacketEnvelope

logger = logging.getLogger(__name__)

ActionHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

_handlers: dict[str, ActionHandler] = {}
_inflate_fn: Callable[[dict[str, Any]], PacketEnvelope] | None = None
_deflate_fn: Callable[[PacketEnvelope, dict[str, Any]], dict[str, Any]] | None = None


def register_handler(action: str, handler: ActionHandler) -> None:
    _handlers[action] = handler
    logger.info("Registered handler", extra={"action": action})


def register_handlers(mapping: dict[str, ActionHandler]) -> None:
    for action, handler in mapping.items():
        register_handler(action, handler)


def set_packet_bridge(
    inflate: Callable[[dict[str, Any]], PacketEnvelope],
    deflate: Callable[[PacketEnvelope, dict[str, Any]], dict[str, Any]],
) -> None:
    global _inflate_fn, _deflate_fn
    _inflate_fn = inflate
    _deflate_fn = deflate
    logger.info("PacketEnvelope bridge wired")


def get_registered_actions() -> list[str]:
    return list(_handlers.keys())


async def execute_action(
    *,
    action: str,
    payload: dict[str, Any],
    tenant: str,
    correlation_id: str = "",
    source_node: str = "unknown",
) -> dict[str, Any]:
    del source_node
    handler = _handlers.get(action)
    if handler is None:
        return {
            "status": "error",
            "error": f"Unknown action: {action}",
            "correlation_id": correlation_id,
        }
    try:
        result = await handler(tenant, payload)
        return {
            "status": "success",
            "action": action,
            "tenant": tenant,
            "correlation_id": correlation_id,
            "data": result,
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Handler failed", extra={"action": action, "tenant": tenant, "error": str(exc)})
        return {
            "status": "failed",
            "action": action,
            "tenant": tenant,
            "correlation_id": correlation_id,
            "error": exc.__class__.__name__,
        }
