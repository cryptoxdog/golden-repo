from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EngineError(Exception):
    action: str
    tenant: str
    client_message: str
    detail: str

    def __str__(self) -> str:
        return f"{self.action} failed for tenant={self.tenant!r}: {self.detail}"
