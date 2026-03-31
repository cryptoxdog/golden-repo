from __future__ import annotations

from pydantic import BaseModel, Field


class ExecuteActionPayload(BaseModel):
    action_name: str = Field(min_length=1)
    parameters: dict


class DescribePayload(BaseModel):
    pass
