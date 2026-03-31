"""
--- L9_META ---
l9_schema: 1
origin: chassis
engine: "*"
layer: [boot]
tags: [chassis, gate, registration, lifecycle, engine-agnostic]
owner: platform-team
status: active
--- /L9_META ---

chassis/gate_client.py — Gate Self-Registration Client

Every L9 engine calls register_with_gate() once at startup.
Reads engine/spec.yaml (NodeSpec), derives the Gate registration
payload, and POSTs to Constellation.Gate.Node POST /v1/admin/register.

Contract (Gate side):
    POST {GATE_URL}/v1/admin/register
    Header: X-Admin-Token: {GATE_ADMIN_TOKEN}   (if configured)
    Body:   RegisterNodesRequest  (dict keyed by node_id)

Behaviour:
    - Non-fatal: if Gate is unreachable, logs a warning and returns.
      The engine continues to start normally so dev/isolation mode works.
    - Retries: up to GATE_REGISTER_RETRIES attempts with exponential
      back-off (1 s, 2 s, 4 s …) before giving up.
    - Re-registration: overwrite=true so rolling restarts are safe.

Env vars (all optional — read via register_from_env()):
    GATE_URL                    e.g. http://gate:8000
    GATE_ADMIN_TOKEN            X-Admin-Token header value
    GATE_NODE_SPEC_PATH         path to engine spec.yaml (default: engine/spec.yaml)
    GATE_REGISTRATION_ENABLED   true / false              (default: true)
    GATE_REGISTER_RETRIES       integer                   (default: 3)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

_DEFAULT_SPEC_PATH = "engine/spec.yaml"
_DEFAULT_RETRIES = 3
_RETRY_BASE_SECONDS = 1.0


# ── spec loading ──────────────────────────────────────────────────────────────

def _load_spec(spec_path: str) -> dict[str, Any]:
    path = Path(spec_path)
    if not path.exists():
        raise FileNotFoundError(f"Node spec not found: {path.resolve()}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Node spec must be a YAML mapping: {path}")
    return raw


def _build_registration_payload(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Derive Gate RegisterNodesRequest body from spec.yaml.

    Gate expects:
        { node_id: { internal_url, supported_actions, priority_class,
                     max_concurrent, health_endpoint, timeout_ms, metadata } }

    spec.yaml must contain a `node` block with at minimum:
        node.id, node.actions
    """
    node = spec.get("node", {})
    if not node:
        raise ValueError("spec.yaml missing required `node` block")

    node_id: str = node.get("id", "")
    if not node_id:
        raise ValueError("spec.yaml `node.id` is required")

    actions: list[str] = node.get("actions", [])
    if not actions:
        raise ValueError(
            f"spec.yaml `node.actions` must not be empty (node: {node_id})"
        )

    # internal_url: explicit > ENGINE_INTERNAL_URL env > service-name convention
    internal_url: str = node.get(
        "internal_url",
        os.getenv("ENGINE_INTERNAL_URL", f"http://{node_id}:8000"),
    )

    return {
        node_id: {
            "internal_url": internal_url,
            "supported_actions": actions,
            "priority_class": node.get("priority_class", "P2"),
            "max_concurrent": node.get("max_concurrent", 50),
            "health_endpoint": node.get("health_endpoint", "/v1/health"),
            "timeout_ms": node.get("timeout_ms", 30000),
            "metadata": {
                "version": node.get("version", "1.0.0"),
                "type": node.get("type", "custom"),
                "generated_by": "l9-chassis",
            },
        }
    }


# ── registration ──────────────────────────────────────────────────────────────

async def register_with_gate(
    *,
    gate_url: str,
    admin_token: str | None = None,
    spec_path: str = _DEFAULT_SPEC_PATH,
    retries: int = _DEFAULT_RETRIES,
    overwrite: bool = True,
) -> bool:
    """
    Load spec.yaml, build payload, POST to Gate /v1/admin/register.

    Returns True on success, False if Gate was unreachable / gave up.
    Never raises — Gate unreachability must not prevent engine startup.
    """
    try:
        spec = _load_spec(spec_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning(
            "gate_client.spec_load_failed: %s — skipping Gate registration", exc
        )
        return False

    try:
        payload = _build_registration_payload(spec)
    except ValueError as exc:
        logger.warning(
            "gate_client.payload_build_failed: %s — skipping Gate registration", exc
        )
        return False

    node_id = next(iter(payload))
    url = f"{gate_url.rstrip('/')}/v1/admin/register"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    params = {"overwrite": "true" if overwrite else "false"}

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params,
                )

            if response.status_code == 200:
                body = response.json()
                healthy = [
                    n["node_name"]
                    for n in body.get("registered", [])
                    if n.get("healthy")
                ]
                logger.info(
                    "gate_client.registered node=%s healthy=%s total_nodes=%s",
                    node_id,
                    healthy,
                    body.get("total_nodes"),
                )
                return True

            if response.status_code in (400, 409, 422):
                logger.error(
                    "gate_client.registration_rejected node=%s status=%s body=%s",
                    node_id,
                    response.status_code,
                    response.text[:500],
                )
                return False

            logger.warning(
                "gate_client.registration_unexpected_status node=%s status=%s attempt=%s/%s",
                node_id,
                response.status_code,
                attempt,
                retries,
            )

        except httpx.TransportError as exc:
            logger.warning(
                "gate_client.connection_failed node=%s attempt=%s/%s error=%s",
                node_id,
                attempt,
                retries,
                exc,
            )

        if attempt < retries:
            backoff = _RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            logger.info("gate_client.retry_backoff seconds=%.1f", backoff)
            await asyncio.sleep(backoff)

    logger.warning(
        "gate_client.gave_up node=%s after %s attempts"
        " — engine continues without Gate registration",
        node_id,
        retries,
    )
    return False


async def register_from_env(
    spec_path: str | None = None,
    gate_url: str | None = None,
    admin_token: str | None = None,
    retries: int | None = None,
) -> bool:
    """
    Convenience wrapper: reads config from explicit args, falling back to env vars.
    Called directly from chassis lifespan — no import of engine internals.

    Parameters
    ----------
    spec_path : str | None
        Path to node spec YAML; falls back to GATE_NODE_SPEC_PATH env var.
    gate_url : str | None
        Gate URL override; falls back to GATE_URL env var.
    admin_token : str | None
        Admin token override; falls back to GATE_ADMIN_TOKEN env var.
    retries : int | None
        Retry count override; falls back to GATE_REGISTER_RETRIES env var.

    Returns True if registration succeeded, False otherwise.
    Gate registration failure is never fatal to engine startup.
    """
    enabled = os.getenv("GATE_REGISTRATION_ENABLED", "true").lower()
    if enabled in ("false", "0", "no"):
        logger.info("gate_client.disabled — skipping Gate registration")
        return False

    resolved_url = gate_url or os.getenv("GATE_URL", "")
    if not resolved_url:
        logger.info(
            "gate_client.no_gate_url"
            " — skipping Gate registration (set GATE_URL to enable)"
        )
        return False

    # Safe-parse retries from env var — fall back to default on invalid value
    if retries is None:
        _raw = os.getenv("GATE_REGISTER_RETRIES", "")
        if _raw:
            try:
                retries = int(_raw)
            except ValueError:
                logger.warning(
                    "gate_client.invalid_retries value=%r — using default %d",
                    _raw,
                    _DEFAULT_RETRIES,
                )
                retries = _DEFAULT_RETRIES
        else:
            retries = _DEFAULT_RETRIES

    return await register_with_gate(
        gate_url=resolved_url,
        admin_token=admin_token or os.getenv("GATE_ADMIN_TOKEN") or None,
        spec_path=spec_path or os.getenv("GATE_NODE_SPEC_PATH", _DEFAULT_SPEC_PATH),
        retries=retries,
    )
