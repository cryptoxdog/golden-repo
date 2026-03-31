from __future__ import annotations

from typing import Awaitable, Callable

from chassis.router import register_handler

DomainHandler = Callable[[str, dict], Awaitable[dict]]
_registry: dict[str, DomainHandler] = {}


def register_action_handler(action: str, handler: DomainHandler) -> None:
    normalized = action.strip().lower()
    _registry[normalized] = handler
    register_handler(normalized, lambda tenant, payload=None, _a=normalized: _registry[_a](tenant, payload))


def register_all() -> None:
    return None
