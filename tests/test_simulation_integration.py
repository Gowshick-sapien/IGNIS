"""Integration tests for Main Dashboard Simulation Control Panel & Multi-Zone UI."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app


@pytest.fixture
def client():
    with patch("src.cloud_dashboard.services.simulation_service.SimulationService._publish_control"):
        with TestClient(app) as c:
            yield c


def test_dashboard_ui_elements_present(client):
    """Verify that the Simulation Drawer, Rich Cards, and Edge Node Grid markup exist."""
    res = client.get("/")
    assert res.status_code == 200
    assert "sim-control-drawer" in res.text
    assert "Live Scenario Simulation Control" in res.text
    assert "btn-scenario-S1" in res.text
    assert "btn-scenario-S2" in res.text
    assert "btn-scenario-S3" in res.text
    assert "btn-scenario-S4" in res.text
    assert "btn-scenario-S6" in res.text
    assert "edge-nodes-container" in res.text
    assert "renderRichZoneCards" in res.text


def test_simulation_status_endpoint(client):
    """Verify simulation status polling for all zones."""
    for zone in ["4A", "4B", "4C"]:
        res = client.get(f"/api/simulation/status?zone_id={zone}")
        assert res.status_code == 200
        data = res.json()
        assert data["zone_id"] == zone
        assert "is_active" in data
        assert "running_scenario" in data


def test_simulation_start_invalid_params(client):
    """Verify validation on invalid zone or scenario."""
    res = client.post("/api/simulation/start", json={"zone_id": "99Z", "scenario_id": "S1"})
    assert res.status_code == 400

    res = client.post("/api/simulation/start", json={"zone_id": "4B", "scenario_id": "INVALID_S99"})
    assert res.status_code == 400


def test_simulation_start_and_stop_lifecycle(client):
    """Verify simulation execution flow with mocked publish."""
    # 1. Start S1 on Zone 4B
    res = client.post("/api/simulation/start", json={"zone_id": "4B", "scenario_id": "S1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    assert data["scenario_id"] == "S1"

    # Check status
    res = client.get("/api/simulation/status?zone_id=4B")
    assert res.status_code == 200
    assert res.json()["running_scenario"] == "S1"

    # 2. Stop S1 on Zone 4B
    res = client.post("/api/simulation/stop", json={"zone_id": "4B"})
    assert res.status_code == 200
    assert res.json()["status"] == "stopped"

    # Check status is now idle
    res = client.get("/api/simulation/status?zone_id=4B")
    assert res.status_code == 200
    assert res.json()["is_active"] is False
