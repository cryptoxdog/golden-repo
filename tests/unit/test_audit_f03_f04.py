"""tests/unit/test_audit_f03_f04.py — F-03/F-04: async handlers + health registered"""
import asyncio
import pytest
from engine.handlers import handle_execute, handle_describe, handle_health, register_all


def test_handle_execute_is_coroutine():
    assert asyncio.iscoroutinefunction(handle_execute)


def test_handle_describe_is_coroutine():
    assert asyncio.iscoroutinefunction(handle_describe)


def test_handle_health_registered():
    registry = register_all()
    assert "health" in registry


@pytest.mark.asyncio
async def test_handle_health_returns_healthy():
    result = await handle_health("tenant_a", {})
    assert result["status"] == "healthy"
    assert result["tenant"] == "tenant_a"
