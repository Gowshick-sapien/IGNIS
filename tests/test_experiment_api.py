"""Integration tests for versioned Experiment REST API endpoints (/api/v1/experiment/*) (Phase G2)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app

client = TestClient(app)


def test_get_status_endpoint():
    response = client.get("/api/v1/experiment/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "state" in data["data"]


def test_run_and_duplicate_conflict():
    # Trigger run
    res = client.post("/api/v1/experiment/run", json={"trials": 1, "seed": 42, "clean": True, "scenarios": "S1"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Trigger second run while active -> 409 Conflict
    conflict_res = client.post("/api/v1/experiment/run", json={"trials": 1, "seed": 42, "clean": True, "scenarios": "S1"})
    assert conflict_res.status_code == 409
    err_body = conflict_res.json()
    assert err_body["error"] in ("ExperimentAlreadyRunning", "InvalidStateTransition")
    assert "message" in err_body

    # Clean up by stopping
    stop_res = client.post("/api/v1/experiment/stop")
    assert stop_res.status_code == 200


def test_invalid_state_transition_contract():
    # Calling pause when IDLE should return 409 with standardized ErrorResponse
    res = client.post("/api/v1/experiment/pause")
    assert res.status_code == 409
    data = res.json()
    assert "error" in data
    assert "message" in data
    assert data["error"] == "InvalidStateTransition"


def test_get_logs_endpoint():
    res = client.get("/api/v1/experiment/logs?tail=20")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "lines" in data["data"]
    assert "total_lines" in data["data"]
