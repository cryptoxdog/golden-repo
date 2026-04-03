from __future__ import annotations
import pytest
from chassis.health import HealthAggregator, HealthStatus


@pytest.mark.asyncio
async def test_all_healthy():
    h = HealthAggregator()
    h.register("db", lambda: _ok())
    result = await h.check()
    assert result["status"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_all_unhealthy():
    h = HealthAggregator()
    h.register("db", lambda: _fail())
    result = await h.check()
    assert result["status"] == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_degraded():
    h = HealthAggregator()
    h.register("db", lambda: _ok())
    h.register("cache", lambda: _fail())
    result = await h.check()
    assert result["status"] == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_probe_exception_counts_as_failure():
    async def bad():
        raise RuntimeError("boom")
    h = HealthAggregator()
    h.register("db", bad)
    result = await h.check()
    assert result["probes"]["db"] is False


@pytest.mark.asyncio
async def test_empty_aggregator_healthy():
    h = HealthAggregator()
    result = await h.check()
    assert result["status"] == HealthStatus.HEALTHY


async def _ok() -> bool:
    return True

async def _fail() -> bool:
    return False
