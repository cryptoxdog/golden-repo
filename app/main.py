"""L9 Engine FastAPI app — production entrypoint with protocol wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import load_config
from app.preflight import run_preflight
from chassis.actions import execute_action, get_registered_actions, set_packet_bridge
from chassis.audit import AuditLogger, LogAuditSink
from chassis.contract_enforcement import enforce_packet_contract
from chassis.health import ContractsProbe, DatabaseProbe, HealthAggregator
from chassis.idempotency import IdempotencyStore
from chassis.types import PacketEnvelope, normalize_packet
from database.init_db import apply_schema
from engine.handlers import init_service, register_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_config = load_config()
_health: HealthAggregator | None = None
_idempotency_store: IdempotencyStore | None = None
_audit_logger: AuditLogger | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _health, _idempotency_store, _audit_logger
    logger.info("Starting L9 engine lifespan")

    run_preflight(_config)
    apply_schema(_config.state_db_path)

    _idempotency_store = IdempotencyStore(_config.state_db_path)
    _idempotency_store.connect()

    _audit_logger = AuditLogger()
    _audit_logger.register_sink(LogAuditSink())

    def inflate(raw: dict[str, object]) -> PacketEnvelope:
        packet = normalize_packet(raw, source_node=_config.node_name)
        violations = enforce_packet_contract(packet, contracts_dir=_config.contracts_dir)
        if violations:
            raise ValueError(f"PacketEnvelope contract violations: {violations}")
        return packet

    def deflate(packet: PacketEnvelope, result: dict[str, object]) -> dict[str, object]:
        return {
            "packet_id": packet.packet_id,
            "correlation_id": packet.correlation_id,
            "status": result.get("status", "success"),
            "data": result.get("data", result),
        }

    set_packet_bridge(inflate, deflate)
    init_service(allowed_actions=_config.allowed_actions)
    register_all()

    _health = HealthAggregator(service_name=_config.service_name, version=_config.service_version)
    _health.register_probe(DatabaseProbe(_config.state_db_path))
    _health.register_probe(ContractsProbe(_config.contracts_dir))
    _health.set_ready()

    logger.info("L9 engine ready", extra={"node": _config.node_name})
    yield

    if _idempotency_store is not None:
        _idempotency_store.close()
    logger.info("L9 engine shutdown complete")


app = FastAPI(title="L9 Golden Repo Engine", version=_config.service_version, lifespan=lifespan)


@app.post("/v1/execute")
async def execute_endpoint(request: Request) -> JSONResponse:
    if _idempotency_store is None:
        return JSONResponse(status_code=503, content={"status": "error", "error": "runtime not initialized"})
    raw = await request.json()
    packet = normalize_packet(raw, source_node=_config.node_name)
    violations = enforce_packet_contract(packet, contracts_dir=_config.contracts_dir)
    if violations:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "error": "PacketEnvelope contract violations", "violations": violations},
        )
    cached = _idempotency_store.check_and_store(
        idempotency_key=packet.idempotency_key,
        tenant_id=packet.tenant.tenant_id,
        packet_id=packet.packet_id,
        source_node=packet.source_node,
    )
    if cached is not None:
        return JSONResponse(content=cached)
    result = await execute_action(
        action=packet.payload.action,
        payload=packet.payload.data,
        tenant=packet.tenant.tenant_id,
        correlation_id=packet.correlation_id,
        source_node=packet.source_node,
    )
    _idempotency_store.store_response(
        idempotency_key=packet.idempotency_key,
        tenant_id=packet.tenant.tenant_id,
        response=result,
    )
    if _audit_logger is not None and result.get("status") == "success":
        _audit_logger.log(
            action=packet.payload.action,
            tenant_id=packet.tenant.tenant_id,
            correlation_id=packet.correlation_id,
            actor=packet.tenant.actor,
            resource="action_execution",
            metadata={"packet_id": packet.packet_id},
        )
    return JSONResponse(content=result)


@app.get("/v1/health")
async def health_endpoint() -> JSONResponse:
    if _health is None:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": "health system not initialized"})
    health_data = _health.evaluate()
    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_data)


@app.get("/v1/actions")
async def actions_endpoint() -> JSONResponse:
    return JSONResponse(content={"node": _config.node_name, "actions": get_registered_actions()})
