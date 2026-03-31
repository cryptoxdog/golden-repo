from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_config
from chassis.actions import execute_action, list_actions, set_packet_bridge
from chassis.contract_enforcement import ContractViolation, enforce_packet_contract
from chassis.health import DependencyProbe, HealthAggregator
from chassis.idempotency import DuplicatePacketError, IdempotencyStore
from chassis.types import PacketEnvelope, TenantSection, build_root_packet
from engine.handlers import register_all
from engine.services.action_service import ActionService

logger = logging.getLogger(__name__)

_health_aggregator: HealthAggregator | None = None
_idempotency_store: IdempotencyStore | None = None


def _inflate(raw: dict[str, Any]) -> PacketEnvelope:
    tenant_raw = raw.get("tenant") or {}
    if isinstance(tenant_raw, str):
        tenant_section = TenantSection(
            actor=tenant_raw, on_behalf_of=tenant_raw, originator=tenant_raw, org_id=tenant_raw
        )
    else:
        tenant_section = TenantSection(
            actor=tenant_raw.get("actor", "unknown"),
            on_behalf_of=tenant_raw.get("on_behalf_of", "unknown"),
            originator=tenant_raw.get("originator", "unknown"),
            org_id=tenant_raw.get("org_id", "unknown"),
        )
    cfg = get_config()
    packet = build_root_packet(
        source_node="ingress",
        destination_node=cfg.node_name,
        action=raw.get("action", "execute"),
        tenant=tenant_section,
        payload=raw.get("payload", {}),
        idempotency_key=raw.get("idempotency_key"),
    )
    enforce_packet_contract(packet)
    assert _idempotency_store is not None
    _idempotency_store.check_and_record(
        idempotency_key=packet.idempotency_key,
        tenant_org_id=packet.tenant.org_id,
        packet_id=packet.packet_id,
        source_node=packet.source_node,
    )
    return packet


def _deflate(packet: PacketEnvelope, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "packet_id": packet.packet_id,
        "correlation_id": packet.correlation_id,
        "data": result,
        "trace": [t.model_dump() for t in packet.trace],
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _health_aggregator, _idempotency_store

    cfg = get_config()
    logging.basicConfig(level=logging.INFO)

    _idempotency_store = IdempotencyStore(cfg.state_db_path)
    _idempotency_store.connect()
    logger.info("idempotency_store_ready", extra={"path": cfg.state_db_path})

    spec_path = os.environ.get("L9_SPEC_PATH", "spec.yaml")
    service = ActionService(spec_path)
    register_all(service)

    set_packet_bridge(_inflate, _deflate)
    logger.info("packet_bridge_wired")

    _health_aggregator = HealthAggregator(cfg.service_name, cfg.service_version)

    async def _db_probe() -> bool:
        try:
            assert _idempotency_store is not None
            assert _idempotency_store._conn is not None
            _idempotency_store._conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    _health_aggregator.register_probe(
        DependencyProbe("sqlite", _db_probe, critical=True)
    )

    logger.info("engine_startup_complete", extra={"service": cfg.service_name})
    yield

    if _idempotency_store:
        _idempotency_store.close()
    logger.info("engine_shutdown_complete")


app = FastAPI(lifespan=lifespan, title="L9 Engine", version="1.0.0")


@app.post("/v1/execute")
async def execute_endpoint(request: Request) -> JSONResponse:
    body: dict[str, Any] = await request.json()
    action = body.get("action", "execute")
    tenant = body.get("tenant", {})
    payload = body.get("payload", {})
    try:
        result = await execute_action(
            action=action,
            tenant=str(tenant),
            payload=payload,
            raw_request=body,
        )
        return JSONResponse(content=result)
    except DuplicatePacketError as exc:
        raise HTTPException(status_code=409, detail=f"Duplicate packet: {exc}") from exc
    except ContractViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("execute_runtime_error", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Internal engine error") from exc


@app.get("/v1/health")
async def health_endpoint() -> JSONResponse:
    if _health_aggregator is None:
        return JSONResponse(
            content={"status": "unhealthy", "reason": "not_initialised"}, status_code=503
        )
    result = await _health_aggregator.check()
    status_code = 200 if result["status"] == "healthy" else 503 if result["status"] == "unhealthy" else 200
    return JSONResponse(content=result, status_code=status_code)


@app.get("/v1/actions")
async def actions_endpoint() -> JSONResponse:
    return JSONResponse(content={"actions": list_actions()})
