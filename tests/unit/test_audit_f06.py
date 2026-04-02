"""tests/unit/test_audit_f06.py — F-06: empty DB password rejected at construction"""
import pytest
from engine.settings import DatabaseConfig


def test_empty_password_raises():
    with pytest.raises((ValueError, Exception)):
        DatabaseConfig(password="")


def test_valid_password_accepted():
    cfg = DatabaseConfig(password="secret123")
    assert cfg.password == "secret123"
