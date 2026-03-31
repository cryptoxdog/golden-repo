from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BaseActionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


class QueryPayload(BaseActionPayload):
    query: str
    limit: int = Field(default=25, ge=1, le=500)


class BatchPayload(BaseActionPayload):
    items: list[dict] = Field(min_length=1, max_length=500)
