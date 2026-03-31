from __future__ import annotations

import logging
import sys

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest
from pythonjsonlogger.json import JsonFormatter
from starlette.responses import Response

from app.config import get_config

REGISTRY = CollectorRegistry(auto_describe=True)
REQUESTS_TOTAL = Counter("l9_requests_total", "Total execute requests", ["service", "action", "status"], registry=REGISTRY)
READY_GAUGE = Gauge("l9_service_ready", "Service readiness", ["service"], registry=REGISTRY)


def configure_logging() -> None:
    cfg = get_config()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s") if True else logging.Formatter("%(message)s"))
    root.addHandler(handler)


def set_readiness(ready: bool) -> None:
    READY_GAUGE.labels(service=get_config().service_name).set(1 if ready else 0)


def record_request(action: str, status: str) -> None:
    REQUESTS_TOTAL.labels(service=get_config().service_name, action=action, status=status).inc()


def metrics_response() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
