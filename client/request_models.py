from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TenantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    on_behalf_of: str | None = None
    originator: str | None = None
    org_id: str
    user_id: str | None = None


class ExecuteOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination_node: str
    source_node: str = "client"
    reply_to: str | None = None
    timeout_ms: int = 30000
    idempotency_key: str | None = None
