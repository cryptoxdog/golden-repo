from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"


class DependencyProbe:
    def __init__(self, name: str, check_fn: Callable[[], Awaitable[bool]], critical: bool = True) -> None:
        self.name = name
        self.check_fn = check_fn
        self.critical = critical


class HealthAggregator:
    def __init__(self, service_name: str, service_version: str) -> None:
        self._service_name = service_name
        self._service_version = service_version
        self._probes: list[DependencyProbe] = []
        self._start_time = time.monotonic()

    def register_probe(self, probe: DependencyProbe) -> None:
        self._probes.append(probe)
        logger.info("health_probe_registered", extra={"probe": probe.name})

    async def check(self) -> dict[str, Any]:
        results: dict[str, bool] = {}
        all_critical_ok = True
        any_degraded = False

        for probe in self._probes:
            try:
                ok = await probe.check_fn()
            except Exception:
                logger.exception("health_probe_error", extra={"probe": probe.name})
                ok = False
            results[probe.name] = ok
            if not ok:
                if probe.critical:
                    all_critical_ok = False
                else:
                    any_degraded = True

        if not all_critical_ok:
            status = HealthStatus.unhealthy
        elif any_degraded:
            status = HealthStatus.degraded
        else:
            status = HealthStatus.healthy

        uptime_seconds = round(time.monotonic() - self._start_time, 1)

        return {
            "status": status.value,
            "service": self._service_name,
            "version": self._service_version,
            "uptime_seconds": uptime_seconds,
            "dependencies": results,
        }
