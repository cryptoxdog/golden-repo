"""tests/unit/test_audit_f02_f05.py — F-02/F-05: no stub /v1/execute in engine/main.py"""
import pytest
from engine.main import app


def test_engine_main_has_no_execute_route():
    routes = {r.path for r in app.routes}
    assert "/v1/execute" not in routes, "engine/main.py must not define /v1/execute (stub removed)"


def test_engine_main_has_health_route():
    routes = {r.path for r in app.routes}
    assert "/health" in routes
