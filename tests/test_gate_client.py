"""
tests/test_gate_client.py — Gate self-registration client tests

Covers:
    - success path: Gate returns 200, node registered
    - retry path: Gate connection fails, gives up after N retries
    - 4xx path: Gate rejects payload, no retry
    - missing spec: spec.yaml not found, non-fatal (returns False)
    - missing node block: spec.yaml malformed, non-fatal
    - empty actions: spec.yaml node.actions missing
    - admin token: X-Admin-Token header sent when configured
    - no token: header absent when token not configured
    - register_from_env: disabled via GATE_REGISTRATION_ENABLED=false
    - register_from_env: no GATE_URL, skips silently
    - register_from_env: full success path via env vars
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from chassis.gate_client import (
    _build_registration_payload,
    _load_spec,
    register_from_env,
    register_with_gate,
)


# ── fixtures / helpers ───────────────────────────────────────────────────────

VALID_SPEC_YAML = textwrap.dedent("""    node:
      id: test_engine
      type: enricher
      version: "1.0.0"
      priority_class: P1
      max_concurrent: 50
      timeout_ms: 8000
      health_endpoint: /v1/health
      actions:
        - enrich_contact
        - enrich_company
""")


def _mock_response(status_code: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = str(body)
    return resp


def _make_async_client(response: MagicMock) -> MagicMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture()
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "spec.yaml"
    p.write_text(VALID_SPEC_YAML)
    return p


# ── unit: _load_spec ─────────────────────────────────────────────────────────

def test_load_spec_success(spec_file: Path) -> None:
    result = _load_spec(str(spec_file))
    assert result["node"]["id"] == "test_engine"


def test_load_spec_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        _load_spec("/nonexistent/path/spec.yaml")


# ── unit: _build_registration_payload ────────────────────────────────────────

def test_build_payload_valid(spec_file: Path) -> None:
    import yaml
    spec = yaml.safe_load(spec_file.read_text())
    payload = _build_registration_payload(spec)
    assert "test_engine" in payload
    entry = payload["test_engine"]
    assert entry["priority_class"] == "P1"
    assert entry["max_concurrent"] == 50
    assert entry["timeout_ms"] == 8000
    assert "enrich_contact" in entry["supported_actions"]
    assert "enrich_company" in entry["supported_actions"]
    assert entry["metadata"]["type"] == "enricher"
    assert entry["metadata"]["generated_by"] == "l9-chassis"
    assert entry["health_endpoint"] == "/v1/health"


def test_build_payload_missing_node_block() -> None:
    with pytest.raises(ValueError, match="missing required `node` block"):
        _build_registration_payload({})


def test_build_payload_missing_id() -> None:
    with pytest.raises(ValueError, match="node.id"):
        _build_registration_payload({"node": {"actions": ["do_thing"]}})


def test_build_payload_empty_actions() -> None:
    with pytest.raises(ValueError, match="node.actions"):
        _build_registration_payload({"node": {"id": "x", "actions": []}})


def test_build_payload_derives_internal_url(spec_file: Path) -> None:
    import yaml
    spec = yaml.safe_load(spec_file.read_text())
    payload = _build_registration_payload(spec)
    # no internal_url in VALID_SPEC_YAML — should derive to http://{id}:8000
    assert payload["test_engine"]["internal_url"] == "http://test_engine:8000"


def test_build_payload_explicit_internal_url(tmp_path: Path) -> None:
    import yaml
    spec_text = VALID_SPEC_YAML + "  internal_url: http://10.0.0.5:9000\n"
    path = tmp_path / "spec.yaml"
    path.write_text(spec_text)
    spec = yaml.safe_load(path.read_text())
    payload = _build_registration_payload(spec)
    assert payload["test_engine"]["internal_url"] == "http://10.0.0.5:9000"


# ── async: register_with_gate ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(spec_file: Path) -> None:
    success_body = {
        "registered": [{"node_name": "test_engine", "healthy": True}],
        "total_nodes": 1,
        "healthy_nodes": 1,
    }
    mock_client = _make_async_client(_mock_response(200, success_body))

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        result = await register_with_gate(
            gate_url="http://gate:8000",
            spec_path=str(spec_file),
        )

    assert result is True
    mock_client.post.assert_called_once()
    url_called = mock_client.post.call_args[0][0]
    assert url_called.endswith("/v1/admin/register")


@pytest.mark.asyncio
async def test_register_sends_admin_token(spec_file: Path) -> None:
    success_body = {
        "registered": [{"node_name": "test_engine", "healthy": True}],
        "total_nodes": 1,
        "healthy_nodes": 1,
    }
    mock_client = _make_async_client(_mock_response(200, success_body))

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        await register_with_gate(
            gate_url="http://gate:8000",
            admin_token="super-secret",
            spec_path=str(spec_file),
        )

    headers_sent = mock_client.post.call_args[1]["headers"]
    assert headers_sent["X-Admin-Token"] == "super-secret"


@pytest.mark.asyncio
async def test_register_no_token_header_absent(spec_file: Path) -> None:
    success_body = {
        "registered": [{"node_name": "test_engine", "healthy": True}],
        "total_nodes": 1,
        "healthy_nodes": 1,
    }
    mock_client = _make_async_client(_mock_response(200, success_body))

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        await register_with_gate(
            gate_url="http://gate:8000",
            admin_token=None,
            spec_path=str(spec_file),
        )

    headers_sent = mock_client.post.call_args[1]["headers"]
    assert "X-Admin-Token" not in headers_sent


@pytest.mark.asyncio
async def test_register_retries_on_transport_error(spec_file: Path) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(
        side_effect=httpx.TransportError("connection refused")
    )

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client),          patch("chassis.gate_client.asyncio.sleep", new=AsyncMock()):
        result = await register_with_gate(
            gate_url="http://gate:8000",
            spec_path=str(spec_file),
            retries=3,
        )

    assert result is False
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_register_gives_up_on_400_no_retry(spec_file: Path) -> None:
    mock_client = _make_async_client(
        _mock_response(400, {"detail": "bad request"})
    )

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        result = await register_with_gate(
            gate_url="http://gate:8000",
            spec_path=str(spec_file),
            retries=3,
        )

    assert result is False
    assert mock_client.post.call_count == 1  # no retry on client error


@pytest.mark.asyncio
async def test_register_gives_up_on_409_no_retry(spec_file: Path) -> None:
    mock_client = _make_async_client(
        _mock_response(409, {"detail": "conflict"})
    )

    with patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        result = await register_with_gate(
            gate_url="http://gate:8000",
            spec_path=str(spec_file),
            retries=3,
        )

    assert result is False
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_register_missing_spec_is_nonfatal() -> None:
    result = await register_with_gate(
        gate_url="http://gate:8000",
        spec_path="/does/not/exist/spec.yaml",
    )
    assert result is False


@pytest.mark.asyncio
async def test_register_malformed_spec_is_nonfatal(tmp_path: Path) -> None:
    bad = tmp_path / "spec.yaml"
    bad.write_text("- just\n- a\n- list\n")
    result = await register_with_gate(
        gate_url="http://gate:8000",
        spec_path=str(bad),
    )
    assert result is False


# ── async: register_from_env ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_from_env_disabled() -> None:
    with patch.dict(os.environ, {"GATE_REGISTRATION_ENABLED": "false"}, clear=False):
        result = await register_from_env()
    assert result is False


@pytest.mark.asyncio
async def test_register_from_env_disabled_zero() -> None:
    with patch.dict(os.environ, {"GATE_REGISTRATION_ENABLED": "0"}, clear=False):
        result = await register_from_env()
    assert result is False


@pytest.mark.asyncio
async def test_register_from_env_no_gate_url() -> None:
    env = {"GATE_REGISTRATION_ENABLED": "true", "GATE_URL": ""}
    with patch.dict(os.environ, env, clear=False):
        # unset GATE_URL entirely if it exists
        os.environ.pop("GATE_URL", None)
        result = await register_from_env()
    assert result is False


@pytest.mark.asyncio
async def test_register_from_env_full_success(spec_file: Path) -> None:
    success_body = {
        "registered": [{"node_name": "test_engine", "healthy": True}],
        "total_nodes": 3,
        "healthy_nodes": 3,
    }
    mock_client = _make_async_client(_mock_response(200, success_body))

    env = {
        "GATE_REGISTRATION_ENABLED": "true",
        "GATE_URL": "http://gate:8000",
        "GATE_ADMIN_TOKEN": "tok",
        "GATE_REGISTER_RETRIES": "2",
    }
    with patch.dict(os.environ, env, clear=False),          patch("chassis.gate_client.httpx.AsyncClient", return_value=mock_client):
        result = await register_from_env(spec_path=str(spec_file))

    assert result is True
    headers_sent = mock_client.post.call_args[1]["headers"]
    assert headers_sent["X-Admin-Token"] == "tok"
