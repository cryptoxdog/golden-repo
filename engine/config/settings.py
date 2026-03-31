from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "golden-repo-ai-review-system"
    spec_path: str = "spec.yaml"
