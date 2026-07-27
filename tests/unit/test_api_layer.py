"""Unit Test Suite for API Layer Endpoints and Controllers."""

import pytest
from fastapi.testclient import TestClient
from src.api_layer import app


@pytest.fixture
def client():
    """Returns TestClient instance for FastAPI application."""
    return TestClient(app)


def test_health_check_endpoint(client):
    """Verifies GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert json_resp["data"]["status"] == "healthy"


def test_system_status_endpoint(client):
    """Verifies GET /api/v1/system/status endpoint."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert "features" in json_resp["data"]


def test_agent_execute_endpoint(client):
    """Verifies POST /api/v1/agent/execute endpoint."""
    payload = {
        "user_query": "Execute system test query",
        "session_id": "test_session_123"
    }
    response = client.post("/api/v1/agent/execute", json=payload)
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert "output" in json_resp["data"]
    assert json_resp["data"]["task_id"].startswith("task_")
