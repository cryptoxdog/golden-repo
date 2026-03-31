from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_config
from app.observability import configure_logging, set_readiness
from app.preflight import run_preflight
from chassis.app import create_chassis_app
from engine.handlers import register_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    configure_logging()
    app.state.adapter_ready = False
    set_readiness(False)
    run_preflight(cfg)
    register_all()
    app.state.adapter_ready = True
    set_readiness(True)
    yield
    app.state.adapter_ready = False
    set_readiness(False)


def create_app() -> FastAPI:
    cfg = get_config()
    return create_chassis_app(service_name=cfg.service_name, version=cfg.service_version, lifespan=lifespan)


app = create_app()
