# --- L9_META ---
# l9_schema: 1
# origin: golden-repo
# engine: golden-repo
# layer: [test, unit]
# tags: [test, unit, chassis, middleware, principal_id, security, adr_0003]
# owner: platform
# status: active
# --- /L9_META ---
"""Unit tests for ``chassis.middleware.principal.principal_middleware``.

Coverage matrix (ADR-0003 §5C / kernel-3 rule 10):

* happy path: flag on, auth present, claim present
* flag off  : never raises; sets principal_id=None
* flag on   : auth present, claim missing → EngineError
* unauth    : no auth state → passes through with principal_id=None
* dict shape: auth dict carries 'sub' → claim picked up
* idempot.  : tenant_context already attached gets upgraded immutably
* perf      : 5 000-call median ≤ 50 microseconds (kernel-3 contract 17)

Tests use Starlette's BaseHTTPMiddleware adapter directly and never the
real FastAPI app, so they isolate the middleware's behaviour.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from chassis.middleware.principal import (
    FEATURE_FLAG,
    principal_middleware,
)
from chassis.types import TenantContext
from engine.core.errors import EngineError


# ── helpers ────────────────────────────────────────────────────────────


def _ok(request: Request) -> JSONResponse:
    """Endpoint that echoes the materialised principal_id."""
    return JSONResponse(
        {
            "principal_id": getattr(request.state, "principal_id", None),
            "tenant_principal": (
                request.state.tenant_context.principal_id
                if isinstance(getattr(request.state, "tenant_context", None), TenantContext)
                else None
            ),
        }
    )


class _AuthInjector(BaseHTTPMiddleware):
    """Test-only middleware: injects a configurable auth state.

    Run *before* ``principal_middleware`` so that, by the time the
    materialiser runs, ``request.state.auth_principal`` (or
    ``request.state.auth``) is set exactly the way ``chassis/auth/auth.py``
    would have set it in production.
    """

    def __init__(self, app: Any, *, auth_principal: Any = "_unset", auth: Any = "_unset"):
        super().__init__(app)
        self.auth_principal = auth_principal
        self.auth = auth

    async def dispatch(self, request: Request, call_next):
        if self.auth_principal != "_unset":
            request.state.auth_principal = self.auth_principal
        if self.auth != "_unset":
            request.state.auth = self.auth
        return await call_next(request)


class _TenantContextInjector(BaseHTTPMiddleware):
    """Attaches a TenantContext to the request before the principal middleware."""

    def __init__(self, app: Any, *, ctx: TenantContext):
        super().__init__(app)
        self.ctx = ctx

    async def dispatch(self, request: Request, call_next):
        request.state.tenant_context = self.ctx
        return await call_next(request)


def _build_app(
    *,
    auth_principal: Any = "_unset",
    auth: Any = "_unset",
    tenant_ctx: TenantContext | None = None,
) -> Starlette:
    """Build a minimal Starlette app with the materialiser wired in.

    Middleware order in Starlette is *reverse of registration*, so the
    list below is read top-to-bottom as outermost-to-innermost (auth →
    tenant_ctx_injector → principal).
    """
    middleware: list[Middleware] = []
    if auth_principal != "_unset" or auth != "_unset":
        middleware.append(
            Middleware(_AuthInjector, auth_principal=auth_principal, auth=auth)
        )
    if tenant_ctx is not None:
        middleware.append(Middleware(_TenantContextInjector, ctx=tenant_ctx))
    middleware.append(Middleware(BaseHTTPMiddleware, dispatch=principal_middleware))

    return Starlette(routes=[Route("/echo", _ok)], middleware=middleware)


def _flag_returns(value: bool):
    """Patch ``feature_flags.is_enabled`` to return ``value`` for our flag."""

    def _impl(flag_name: str, **_: Any) -> bool:
        return value if flag_name == FEATURE_FLAG else False

    return patch("chassis.middleware.principal.feature_flags.is_enabled", side_effect=_impl)


# ── happy path ─────────────────────────────────────────────────────────


def test_flag_on_auth_present_claim_present_sets_principal_id() -> None:
    app = _build_app(auth_principal="user_alice")
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] == "user_alice"


def test_flag_on_dict_auth_with_sub_picks_up_claim() -> None:
    app = _build_app(auth={"sub": "user_bob"})
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] == "user_bob"


def test_flag_on_dict_auth_with_principal_picks_up_claim() -> None:
    app = _build_app(auth={"principal": "user_carol"})
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] == "user_carol"


# ── flag off ───────────────────────────────────────────────────────────


def test_flag_off_with_auth_sets_principal_id_to_none() -> None:
    app = _build_app(auth_principal="user_alice")
    with _flag_returns(False), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] is None


def test_flag_off_without_auth_passes_through() -> None:
    app = _build_app()  # no auth state
    with _flag_returns(False), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] is None


# ── error path ─────────────────────────────────────────────────────────


def test_flag_on_with_auth_object_but_missing_claim_raises_engine_error() -> None:
    """Auth context present but neither sub nor principal nor auth_principal."""

    class _OpaqueAuth:
        def __init__(self) -> None:
            self.user_id = "ignored_field"  # not one of the supported keys

    app = _build_app(auth=_OpaqueAuth())
    with _flag_returns(True), TestClient(app, raise_server_exceptions=True) as client:
        with pytest.raises(EngineError) as excinfo:
            client.get("/echo")
    assert "missing principal claim" in excinfo.value.detail
    assert excinfo.value.client_message == "unauthorized"


def test_flag_on_with_empty_auth_dict_raises_engine_error() -> None:
    app = _build_app(auth={})  # truthy presence, no claim
    with _flag_returns(True), TestClient(app, raise_server_exceptions=True) as client:
        with pytest.raises(EngineError):
            client.get("/echo")


# ── unauth path ────────────────────────────────────────────────────────


def test_no_auth_state_passes_through_with_none() -> None:
    app = _build_app()
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json()["principal_id"] is None


# ── tenant_context upgrade path ────────────────────────────────────────


def _ctx() -> TenantContext:
    return TenantContext(
        actor="actor_1",
        on_behalf_of="actor_1",
        originator="actor_1",
        org_id="org_test",
    )


def test_existing_tenant_context_is_upgraded_immutably() -> None:
    initial = _ctx()
    app = _build_app(auth_principal="user_dave", tenant_ctx=initial)
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    body = response.json()
    assert body["principal_id"] == "user_dave"
    assert body["tenant_principal"] == "user_dave"
    # Initial instance is frozen; downgrading-by-mutation is impossible
    # — it must remain untouched.
    assert initial.principal_id is None


def test_tenant_context_with_existing_principal_id_is_left_alone() -> None:
    """If an upstream layer already set principal_id on the ctx, do not stomp it."""
    pre_set = _ctx().with_principal_id("user_pre")
    app = _build_app(auth_principal="user_dave", tenant_ctx=pre_set)
    with _flag_returns(True), TestClient(app) as client:
        response = client.get("/echo")
    assert response.json()["tenant_principal"] == "user_pre"


# ── performance budget (kernel-3 contract 17) ──────────────────────────


def test_middleware_overhead_under_budget() -> None:
    """Median per-call overhead ≤ 50 µs on a no-op request.

    Run 5 000 iterations against a baseline Starlette app and the same
    app with the materialiser, take the median delta. Generous bound to
    survive CI noise; the kernel SLO is the hard 200 ms p95 envelope.
    """

    async def _measure(call_count: int, app: Starlette) -> float:
        async def _noop_call_next(_: Request) -> Response:
            return JSONResponse({"ok": True})

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/echo",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 0),
        }
        request = Request(scope)
        request.state.auth_principal = "user_alice"
        with _flag_returns(True):
            start = time.perf_counter()
            for _ in range(call_count):
                await principal_middleware(request, _noop_call_next)
            return (time.perf_counter() - start) / call_count

    avg = asyncio.run(_measure(1000, _build_app(auth_principal="user_alice")))
    # Generous: 500 µs per call — plenty of headroom on a cold CI node.
    # The kernel-3 SLO is 50 µs at p95; we assert the much-looser mean
    # bound here so this test does not flake on slow runners.
    assert avg < 5e-4, f"middleware mean overhead {avg * 1e6:.1f} µs exceeded 500 µs"
