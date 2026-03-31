"""
--- L9_META ---
l9_schema: 1
origin: chassis
engine: "*"
layer: [api]
tags: [api, fastapi, chassis, single-ingress, engine-agnostic]
owner: platform-team
status: active
--- /L9_META ---

chassis/app.py — Reusable, Micro-Service Agnostic L9 Chassis

Single-ingress HTTP boundary for ANY L9 constellation engine.
Zero engine imports.  All engine coupling flows through two seams:

    1. LifecycleHook — engine tells the chassis how to start/stop.
    2. execute_action  — chassis calls the engine's action router.

Gate self-registration (new):
    On every engine startup the chassis calls gate_client.register_from_env()
    AFTER hook.startup() completes.  Non-fatal — if GATE_URL is not set or
    Gate is unreachable the engine starts normally.

    Env vars:
        GATE_URL                    http://gate:8000
        GATE_ADMIN_TOKEN            X-Admin-Token value        (optional)
        GATE_NODE_SPEC_PATH         path to spec.yaml          (default: engine/spec.yaml)
        GATE_REGISTRATION_ENABLED   true / false               (default: true)
        GATE_REGISTER_RETRIES       integer                    (default: 3)

Usage (Graph engine):
    from chassis.app import create_app
    from myengine.boot import GraphLifecycle
    app = create_app(lifecycle_hook=GraphLifecycle())

Usage (uvicorn --factory):
    L9_LIFECYCLE_HOOK=myengine.boot:GraphLifecycle
    uvicorn chassis.app:create_app --factory
"""

from __future__ import annotations

import importlib
import logging
import os
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from chassis.gate_client import register_from_env

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  CHASSIS-OWNED CONFIGURATION  (engine never touches this)
# ═══════════════════════════════════════════════════════════════════════════

class ChassisSettings(BaseSettings):
    """
    Minimal config the chassis itself needs.
    Engine-specific settings live in the engine's own Settings class.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- API surface ---
    api_title: str = "L9 Engine"
    api_description: str = "Domain-agnostic L9 chassis"
    api_version: str = "1.1.0"

    # --- CORS ---
    cors_origins: list[str] = []

    # --- Lifecycle hook (dotted path  module.path:ClassName) ---
    l9_lifecycle_hook: str = ""

    # --- Gate self-registration ---
    gate_url: str = ""
    gate_admin_token: str = ""
    gate_node_spec_path: str = "engine/spec.yaml"
    gate_registration_enabled: bool = True
    gate_register_retries: int = 3


_chassis_settings = ChassisSettings()


# ═══════════════════════════════════════════════════════════════════════════
#  CHASSIS-OWNED ENVELOPE MODELS
# ═══════════════════════════════════════════════════════════════════════════

class ExecuteRequest(BaseModel):
    """Universal execute request envelope — chassis contract."""

    action: str
    tenant: str
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class ExecuteResponse(BaseModel):
    """Universal execute response envelope — chassis contract."""

    status: str
    action: str
    tenant: str
    data: dict[str, Any]
    meta: dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════
#  LIFECYCLE HOOK — the engine's ONLY coupling surface to the chassis
# ═══════════════════════════════════════════════════════════════════════════

class LifecycleHook(ABC):
    """
    Abstract contract that every L9 engine implements ONCE.

    The chassis calls:
        startup()   — engine wires its own drivers, loaders, schedulers
        shutdown()  — engine tears down connections
        execute()   — chassis forwards every /v1/execute payload here

    This is the single integration seam.  The chassis has ZERO knowledge
    of Neo4j, DomainPackLoader, GraphDriver, or any engine internals.
    """

    @abstractmethod
    async def startup(self) -> None:
        """Engine-specific initialization (connect DB, load domains, etc.)."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Engine-specific teardown (close pools, flush queues, etc.)."""

    @abstractmethod
    async def execute(
        self,
        action: str,
        payload: dict[str, Any],
        tenant: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Execute an action and return the canonical envelope dict:
            {status, action, tenant, data, meta}
        """

    async def health(self, tenant: str, trace_id: str) -> dict[str, Any]:
        """
        Optional override.  Default delegates to execute(action="health").
        Engines that want a cheaper probe can override this directly.
        """
        return await self.execute(
            action="health",
            payload={},
            tenant=tenant,
            trace_id=trace_id,
        )


class _NoOpLifecycle(LifecycleHook):
    """Fallback when no hook is provided — passes smoke tests, nothing else."""

    async def startup(self) -> None:
        logger.warning("No LifecycleHook configured — chassis running in stub mode")

    async def shutdown(self) -> None:
        # No-op: stub mode has no resources to tear down; cleanup is handled by the engine hook.
        pass

    async def execute(
        self,
        action: str,
        payload: dict[str, Any],
        tenant: str,
        trace_id: str,
    ) -> dict[str, Any]:
        return {
            "status": "failed",
            "action": action,
            "tenant": tenant,
            "data": {"error": "No engine lifecycle hook configured"},
            "meta": {"trace_id": trace_id},
        }


# ═══════════════════════════════════════════════════════════════════════════
#  HOOK RESOLUTION  (env var → importlib → instance)
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_hook(hook: LifecycleHook | None) -> LifecycleHook:
    """
    Priority:
        1. Explicit instance passed to create_app()
        2. L9_LIFECYCLE_HOOK env var  (e.g. "myengine.boot:GraphLifecycle")
        3. _NoOpLifecycle fallback
    """
    if hook is not None:
        return hook

    dotted = _chassis_settings.l9_lifecycle_hook or os.getenv("L9_LIFECYCLE_HOOK", "")
    if dotted:
        try:
            module_path, class_name = dotted.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls()
            logger.info(
                "Resolved LifecycleHook from %s → %s", dotted, type(instance).__name__
            )
            return instance
        except Exception:
            logger.exception("Failed to resolve L9_LIFECYCLE_HOOK=%s", dotted)
            raise

    return _NoOpLifecycle()


# ═══════════════════════════════════════════════════════════════════════════
#  APPLICATION FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def create_app(
    *,
    lifecycle_hook: LifecycleHook | None = None,
    settings: ChassisSettings | None = None,
) -> FastAPI:
    """
    Factory function for the L9 chassis.

    Parameters
    ----------
    lifecycle_hook : LifecycleHook | None
        Engine-supplied hook.  If None, resolved from L9_LIFECYCLE_HOOK env.
    settings : ChassisSettings | None
        Override chassis settings (useful for testing).  Defaults to module-level singleton.
    """
    cfg = settings or _chassis_settings
    hook = _resolve_hook(lifecycle_hook)

    # --- lifespan -----------------------------------------------------------

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("Chassis starting — lifecycle: %s", type(hook).__name__)
        await hook.startup()
        logger.info("Chassis ready")

        # Gate self-registration — non-fatal, runs after engine is fully up
        if cfg.gate_registration_enabled and cfg.gate_url:
            await register_from_env(spec_path=cfg.gate_node_spec_path or None)
        else:
            logger.debug("gate_client.skipped — GATE_URL not configured")

        yield

        logger.info("Chassis shutting down…")
        await hook.shutdown()
        logger.info("Chassis shutdown complete")

    # --- app ----------------------------------------------------------------

    application = FastAPI(
        title=cfg.api_title,
        description=cfg.api_description,
        version=cfg.api_version,
        lifespan=lifespan,
    )

    # --- CORS (conditional) -------------------------------------------------

    if cfg.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins,
            allow_credentials=False,
            allow_methods=["POST", "GET"],
            allow_headers=["*"],
        )

    # --- POST /v1/execute  (single ingress) ---------------------------------

    @application.post(
        "/v1/execute",
        response_model=ExecuteResponse,
        responses={
            400: {"description": "Bad Request — unknown or invalid action"},
            422: {"description": "Unprocessable Entity — payload validation failure"},
            500: {"description": "Internal Server Error — unhandled engine error"},
        },
    )
    async def execute(request: ExecuteRequest) -> ExecuteResponse | JSONResponse:
        """
        Universal action endpoint — single ingress for every engine action.

        Status-code mapping:
            200  — success
            400  — unknown / invalid action  (ValueError from engine)
            422  — payload validation failure (keyword "validation" or "invalid")
            500  — unhandled engine error
        """
        trace_id = request.trace_id or f"trace_{uuid.uuid4().hex[:12]}"

        try:
            result = await hook.execute(
                action=request.action,
                payload=request.payload,
                tenant=request.tenant,
                trace_id=trace_id,
            )

            if result.get("status") == "failed":
                error_detail = result.get("data", {}).get(
                    "error", "Handler execution failed"
                )
                if "validation" in error_detail.lower() or "invalid" in error_detail.lower():
                    raise HTTPException(status_code=422, detail=error_detail)
                raise HTTPException(status_code=500, detail=error_detail)

            return ExecuteResponse(**result)

        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Execute failed: %s", exc)
            raise HTTPException(status_code=500, detail="Internal server error") from exc

    # --- GET /v1/health  (unauthenticated) ----------------------------------

    @application.get("/v1/health")
    async def health(request: Request) -> JSONResponse:
        """
        Health probe.  Delegates to hook.health() so the engine controls
        what "healthy" means.  Kubernetes-compatible: 200 = live, 503 = not.
        """
        tenant = request.query_params.get("tenant", "default")
        trace_id = f"health_{uuid.uuid4().hex[:8]}"

        try:
            result = await hook.health(tenant=tenant, trace_id=trace_id)
            status_code = (
                200
                if result.get("data", {}).get("status") == "healthy"
                else 503
            )
            return JSONResponse(content=result, status_code=status_code)

        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "error": "health_check_failed",
                },
                status_code=503,
            )

    return application
