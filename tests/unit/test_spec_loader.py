from __future__ import annotations

from engine.config.loader import SpecLoader


def test_spec_loader_reads_actions() -> None:
    loader = SpecLoader("spec.yaml")
    assert loader.action_names() == ["execute", "describe"]
