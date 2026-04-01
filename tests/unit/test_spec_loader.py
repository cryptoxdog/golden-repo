from __future__ import annotations

from engine.config.loader import SpecLoader


def test_spec_loader_reads_actions() -> None:
    loader = SpecLoader("spec.yaml")
    # FIX: method is get_allowed_actions(), not action_names()
    actions = loader.get_allowed_actions()
    assert "execute" in actions
    assert "describe" in actions
