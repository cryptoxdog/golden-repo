from __future__ import annotations

import asyncio

from engine.handlers import handle_describe, handle_execute, register_all


def test_register_all_registers_spec_actions() -> None:
    registry = register_all()
    assert set(registry) == {"execute", "describe"}


def test_handle_execute_accepts_known_action() -> None:
    payload = {"action_name": "execute", "parameters": {"value": 1}}
    result = asyncio.run(handle_execute("tenant_a", payload))
    assert result["accepted"] is True
    assert result["action_name"] == "execute"


def test_handle_describe_lists_actions() -> None:
    result = asyncio.run(handle_describe("tenant_a", {}))
    assert result["service"] == "golden-repo-ai-review-system"
    assert set(result["actions"]) == {"execute", "describe"}
