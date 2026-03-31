from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ActionResult:
    accepted: bool
    action_name: str
    parameters: dict

    def to_dict(self) -> dict:
        return asdict(self)
