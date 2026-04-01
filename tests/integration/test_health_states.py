from __future__ import annotations

import pytest
from chassis.health import DependencyProbe, HealthAggregator, HealthStatus


@pytest.mark.asyncio
async def test_healthy_when_all_probes_pass():
    agg = HealthAggregator("svc", "1.0.0")
    agg.register_probe(DependencyProbe("db", lambda: _ok(), critical=True))
    result = await agg.check()
    assert result["status"] == HealthStatus.healthy.value


@pytest.mark.asyncio
async def test_unhealthy_when_critical_probe_fails():
    agg = HealthAggregator("svc", "1.0.0")
    agg.register_probe(DependencyProbe("db", lambda: _fail(), critical=True))
    result = await agg.check()
    assert result["status"] == HealthStatus.unhealthy.value


@pytest.mark.asyncio
async def test_degraded_when_non_critical_probe_fails():
    agg = HealthAggregator("svc", "1.0.0")
    agg.register_probe(DependencyProbe("db", lambda: _ok(), critical=True))
    agg.register_probe(DependencyProbe("cache", lambda: _fail(), critical=False))
    result = await agg.check()
    assert result["status"] == HealthStatus.degraded.value


@pytest.mark.asyncio
async def test_health_payload_includes_required_fields():
    agg = HealthAggregator("my-svc", "2.0.0")
    result = await agg.check()
    assert "status" in result
    assert "service" in result
    assert "version" in result
    assert "uptime_seconds" in result
    assert "dependencies" in result
    assert result["service"] == "my-svc"


async def _ok() -> bool:
    return True


async def _fail() -> bool:
    return False
