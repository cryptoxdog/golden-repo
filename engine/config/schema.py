from __future__ import annotations

from pydantic import BaseModel, Field


class ActionSpec(BaseModel):
    name: str = Field(min_length=1)
    description: str
    input_schema: dict
    output_schema: dict


class ServiceSpec(BaseModel):
    name: str
    version: str
    description: str


class RootSpec(BaseModel):
    service: ServiceSpec
    actions: list[ActionSpec]
