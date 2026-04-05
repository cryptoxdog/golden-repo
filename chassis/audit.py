"""Audit event logger with pluggable sinks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AuditSink(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


class LogAuditSink:
    def emit(self, event: dict[str, Any]) -> None:
        logger.info("AUDIT", extra={"audit_event": event})


class AuditLogger:
    def __init__(self) -> None:
        self._sinks: list[AuditSink] = []

    def register_sink(self, sink: AuditSink) -> None:
        self._sinks.append(sink)

    def log(
        self,
        *,
        action: str,
        tenant_id: str,
        correlation_id: str,
        actor: str,
        resource: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "actor": actor,
            "resource": resource,
            "before_state": before_state,
            "after_state": after_state,
            "metadata": metadata or {},
        }
        for sink in self._sinks:
            sink.emit(event)
