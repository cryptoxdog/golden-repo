from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AuditEvent:
    __slots__ = (
        "who", "what", "when", "tenant", "correlation_id",
        "before_state", "after_state", "packet_id", "node",
    )

    def __init__(
        self,
        *,
        who: str,
        what: str,
        tenant: str,
        correlation_id: str,
        packet_id: str,
        node: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
    ) -> None:
        self.who = who
        self.what = what
        self.when = datetime.now(timezone.utc).isoformat()
        self.tenant = tenant
        self.correlation_id = correlation_id
        self.before_state = before_state
        self.after_state = after_state
        self.packet_id = packet_id
        self.node = node

    def to_dict(self) -> dict[str, Any]:
        return {
            "who": self.who,
            "what": self.what,
            "when": self.when,
            "tenant": self.tenant,
            "correlation_id": self.correlation_id,
            "packet_id": self.packet_id,
            "node": self.node,
            "before_state": self.before_state,
            "after_state": self.after_state,
        }


class AuditLogger:
    def __init__(self, node_name: str) -> None:
        self._node = node_name
        self._sinks: list[Any] = []

    def add_sink(self, sink: Any) -> None:
        self._sinks.append(sink)

    def log(
        self,
        *,
        who: str,
        what: str,
        tenant: str,
        correlation_id: str,
        packet_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            who=who,
            what=what,
            tenant=tenant,
            correlation_id=correlation_id,
            packet_id=packet_id,
            node=self._node,
            before_state=before_state,
            after_state=after_state,
        )
        event_dict = event.to_dict()
        logger.info("audit_event", extra=event_dict)
        for sink in self._sinks:
            try:
                sink(event_dict)
            except Exception:
                logger.exception("audit_sink_failed")
