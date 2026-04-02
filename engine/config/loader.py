from __future__ import annotations
import threading
from pathlib import Path
from typing import Optional
import yaml
from engine.config.schema import RootSpec


class SpecLoader:
    _cache: Optional[RootSpec] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, spec_path: str | Path = "spec.yaml") -> None:
        self._spec_path = Path(spec_path)

    def load(self) -> RootSpec:
        if SpecLoader._cache is not None:
            return SpecLoader._cache
        with SpecLoader._lock:
            if SpecLoader._cache is not None:
                return SpecLoader._cache
            if not self._spec_path.exists():
                raise FileNotFoundError(
                    f"spec.yaml not found at {self._spec_path} — engine cannot start"
                )
            with self._spec_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            SpecLoader._cache = RootSpec.model_validate(data)
            return SpecLoader._cache

    def action_names(self) -> list[str]:
        return [action.name for action in self.load().actions]
