from __future__ import annotations

import asyncio

from engine.handlers import handle_execute


def test_execute_contract_round_trip() -> None:
    payload = {
        "action_name": "describe",
        "parameters": {"limit": 5},
    }
    result = asyncio.run(handle_execute("tenant_a", payload))
    assert result == {
        "accepted": True,
        "action_name": "describe",
        "parameters": {"limit": 5},
    }
