from __future__ import annotations

import asyncio

from engine.handlers import handle_describe, handle_execute, register_all
from engine.services.action_service import ActionService


def _make_service() -> ActionService:
    """Create a test ActionService from the real spec.yaml."""
    return ActionService("spec.yaml")


def test_register_all_registers_spec_actions() -> None:
    # FIX: register_all() requires an ActionService argument (signature changed in PR #36)
    service = _make_service()
    register_all(service)
    from chassis.actions import list_actions
    actions = list_actions()
    assert set(actions) >= {"execute", "describe"}


def test_handle_execute_accepts_known_action() -> None:
    service = _make_service()
    register_all(service)
    payload = {"action_name": "execute", "parameters": {"value": 1}}
    result = asyncio.run(handle_execute("tenant_a", payload))
    assert "action" in result or "status" in result


def test_handle_describe_lists_actions() -> None:
    service = _make_service()
    register_all(service)
    result = asyncio.run(handle_describe("tenant_a", {}))
    assert "service" in result
    assert "allowed_actions" in result or "actions" in result
