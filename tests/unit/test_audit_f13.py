"""tests/unit/test_audit_f13.py — F-13: SpecLoader cache + missing file guard"""
import pytest
from pathlib import Path
from engine.config.loader import SpecLoader


def test_missing_spec_raises(tmp_path):
    SpecLoader._cache = None
    loader = SpecLoader(spec_path=tmp_path / "nonexistent.yaml")
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_spec_cached_after_load(tmp_path):
    SpecLoader._cache = None
    spec = tmp_path / "spec.yaml"
    spec.write_text("service:\n  name: test\n  version: 1.0\nactions: []\n")
    loader = SpecLoader(spec_path=spec)
    s1 = loader.load()
    s2 = loader.load()
    assert s1 is s2
    SpecLoader._cache = None
