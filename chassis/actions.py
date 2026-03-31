from __future__ import annotations

import logging
import time
from typing import Any, Callable, Awaitable

from chassis.types import PacketEnvelope, PacketType, build_root_packet, TenantSection

logger = logging.getLogger(__name__)

HandlerFn = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

_handler_registry: dict[str, HandlerFn] = {}
_inflate_fn: Callable[[dict[str, Any]], PacketEnvelope] | None = None
_deflate_fn: Callable[[PacketEnvelope, dict[str, Any]], dict[str, Any]] | None = None


def set_packet_bridge(
    inflate: Callable[[dict[str, Any]], PacketEnvelope],
    deflate: Callable[[PacketEnvelope, dict[str, Any]], dict[str, Any]],
) -> None:
    global _inflate_fn, _deflate_fn
    _inflate_fn = inflate
    _deflate_fn = deflate
    logger.info("packet_bridge_registered")


def register_handler(action: str, fn: HandlerFn) -> None:
    if action in _handler_registry:
        raise ValueError(f"Handler already registered for action '{action}'")
    _handler_registry[action] = fn
    logger.info("handler_registered", extra={"action": action})


def register_handlers(mapping: dict[str, HandlerFn]) -> None:
    for action, fn in mapping.items():
        register_handler(action, fn)


def get_handler(action: str) -> HandlerFn | None:
    return _handler_registry.get(action)


def list_actions() -> list[str]:
    return list(_handler_registry.keys())


async def execute_action(
    action: str,
    tenant: str,
    payload: dict[str, Any],
    raw_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _inflate_fn is None:
        raise RuntimeError(
            "PacketEnvelope bridge not initialised — call set_packet_bridge() at startup"
        )

    packet = _inflate_fn(raw_request or {"action": action, "tenant_str": tenant, "payload": payload})
    handler = _handler_registry.get(action)
    if handler is None:
        raise KeyError(f"No handler registered for action '{action}'")

    start = time.monotonic()
    try:
        result = await handler(packet.tenant.org_id, packet.payload)
        duration_ms = (time.monotonic() - start) * 1000
        packet.append_trace(packet.destination_node, action, duration_ms=duration_ms, status="ok")
        if _deflate_fn is not None:
            return _deflate_fn(packet, result)
        return {"status": "ok", "data": result, "packet_id": packet.packet_id}
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        packet.append_trace(packet.destination_node, action, duration_ms=duration_ms, status="failed")
        logger.exception("handler_failed", extra={"action": action, "tenant": tenant})
        raise RuntimeError(f"Handler '{action}' failed: {type(exc).__name__}") from exc
