# --- L9_META ---
# l9_schema: 1
# layer: [api]
# tags: [fastapi, chassis, entrypoint]
# status: active
# --- /L9_META ---
"""L9 Golden Repo — FastAPI entrypoint. Replace APP_NAME and wire your engine."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from engine.config.settings import settings

logger = structlog.get_logger()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.app_name})

