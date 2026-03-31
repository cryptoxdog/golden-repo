from __future__ import annotations

from pathlib import Path

import yaml

from engine.config.schema import RootSpec


class SpecLoader:
    def __init__(self, spec_path: str | Path = "spec.yaml") -> None:
        self._spec_path = Path(spec_path)

    def load(self) -> RootSpec:
        with self._spec_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        return RootSpec.model_validate(data)

    def action_names(self) -> list[str]:
        return [action.name for action in self.load().actions]
