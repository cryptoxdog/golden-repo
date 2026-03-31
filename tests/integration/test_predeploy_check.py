from __future__ import annotations

from scripts.predeploy_check import main


def test_predeploy_check_bad_module(monkeypatch):
    monkeypatch.setenv('APP_MODULE', 'missing.module:app')
    assert main() == 1
