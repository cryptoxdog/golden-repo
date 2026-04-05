"""Three-state health aggregator with pluggable probes."""

from __future__ import annotations

import time
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthProbe(Protocol):
    @property
    def name(self) -> str: ...

    def check(self) -> tuple[HealthStatus, str]: ...


class DatabaseProbe:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "database"

    def check(self) -> tuple[HealthStatus, str]:
        import sqlite3

        try:
            conn = sqlite3.connect(self._db_path, timeout=2)
            conn.execute("SELECT 1")
            conn.close()
            return HealthStatus.HEALTHY, "ok"
        except Exception as exc:  # pragma: no cover - defensive
            return HealthStatus.UNHEALTHY, str(exc)


class ContractsProbe:
    def __init__(self, contracts_dir: str) -> None:
        self._contracts_dir = contracts_dir

    @property
    def name(self) -> str:
        return "contracts"

    def check(self) -> tuple[HealthStatus, str]:
        path = Path(self._contracts_dir)
        if not path.is_dir():
            return HealthStatus.UNHEALTHY, f"{self._contracts_dir} not found"
        yamls = list(path.glob("*.yaml"))
        if not yamls:
            return HealthStatus.DEGRADED, "no contract files found"
        return HealthStatus.HEALTHY, f"{len(yamls)} contracts loaded"


class HealthAggregator:
    def __init__(self, *, service_name: str, version: str) -> None:
        self._service_name = service_name
        self._version = version
        self._probes: list[HealthProbe] = []
        self._start_time = time.monotonic()
        self._ready = False

    def register_probe(self, probe: HealthProbe) -> None:
        self._probes.append(probe)

    def set_ready(self) -> None:
        self._ready = True

    def evaluate(self) -> dict[str, Any]:
        probe_results: dict[str, Any] = {}
        worst = HealthStatus.HEALTHY
        for probe in self._probes:
            status, detail = probe.check()
            probe_results[probe.name] = {"status": status.value, "detail": detail}
            if status == HealthStatus.UNHEALTHY:
                worst = HealthStatus.UNHEALTHY
            elif status == HealthStatus.DEGRADED and worst != HealthStatus.UNHEALTHY:
                worst = HealthStatus.DEGRADED
        if not self._ready:
            worst = HealthStatus.UNHEALTHY
        return {
            "status": worst.value,
            "service": self._service_name,
            "version": self._version,
            "uptime_seconds": round(time.monotonic() - self._start_time, 2),
            "ready": self._ready,
            "probes": probe_results,
        }
