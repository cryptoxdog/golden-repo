"""Basic health check tests."""
from fastapi.testclient import TestClient

from engine.main import app

client = TestClient(app)


def test_health():
    # FIX: endpoint is /v1/health not /health (engine.main mounts at /v1/)
    response = client.get("/v1/health")
    assert response.status_code in (200, 503)  # 503 = degraded but reachable
    data = response.json()
    assert "status" in data
