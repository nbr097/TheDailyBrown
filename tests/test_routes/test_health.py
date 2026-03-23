from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app


def test_health_returns_detailed_system_status():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "systems" in data
    assert "openweathermap" in data["systems"]
    assert "microsoft_graph" in data["systems"]
