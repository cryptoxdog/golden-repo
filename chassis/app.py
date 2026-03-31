from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_config
from app.errors import packet_error_payload, raise_http_exception
from app.health import health_payload, readiness_payload
from app.observability import metrics_response, record_request, set_readiness
from .router import execute_handler, inflate_ingress


def create_chassis_app(*, service_name: str, version: str, lifespan: Callable[[FastAPI], AbstractAsyncContextManager[Any]] | None) -> FastAPI:
    app = FastAPI(title=service_name, version=version, lifespan=lifespan)
    app.state.adapter_ready = False

    @app.get("/v1/health")
    async def health() -> dict[str, Any]:
        return health_payload(adapter_ready=bool(getattr(app.state, "adapter_ready", False)))

    @app.get("/v1/readiness")
    async def readiness() -> dict[str, Any]:
        return readiness_payload()

    @app.get("/metrics")
    async def metrics():
        if not get_config().enable_metrics:
            raise HTTPException(status_code=404, detail="Not found")
        return metrics_response()

    @app.post("/v1/execute")
    async def execute(request: Request):
        packet = None
        try:
            packet = inflate_ingress(await request.json())
            response_packet = await execute_handler(packet)
            record_request(packet.header.action, "success")
            return JSONResponse(content=response_packet.dict())
        except Exception as exc:  # noqa: BLE001
            if packet is not None:
                record_request(packet.header.action, "failure")
                return JSONResponse(status_code=200, content=packet_error_payload(exc))
            raise_http_exception(exc, status_code=400, code="invalid_request")

    return app
