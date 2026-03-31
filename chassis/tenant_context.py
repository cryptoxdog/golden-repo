from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TenantContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    actor: str
    on_behalf_of: str
    originator: str
    org_id: str
    user_id: str | None = None


def ensure_tenant_context(value: str | dict | TenantContext) -> TenantContext:
    if isinstance(value, TenantContext):
        return value
    if isinstance(value, str):
        return TenantContext(actor=value, on_behalf_of=value, originator=value, org_id=value)
    return TenantContext(**value)
