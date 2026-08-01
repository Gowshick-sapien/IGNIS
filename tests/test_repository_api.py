"""Integration tests for Repository REST API (Phase G4)."""

import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient

from src.cloud_dashboard.app import app
from src.cloud_dashboard.services.repository_manager import RepositoryManager


@pytest.fixture
def api_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = os.path.join(tmpdir, "workspace")
        results_dir = os.path.join(workspace_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        metrics_data = {
            "overall_verdict": "PASS",
            "experiment_metadata": {"timestamp": "2026-07-31T15:00:00Z", "trial_count": 5, "total_duration_sec": 8.0},
            "scenario_results": {"S3": {"verdict": "PASS", "duration_sec": 8.0, "trials_run": 5}}
        }
        with open(os.path.join(results_dir, "metrics.json"), "w") as f:
            json.dump(metrics_data, f)

        manifest_data = {
            "timestamp": "2026-07-31T15:00:00Z",
            "git_commit": "c4d5e6f7",
            "trial_count": 5,
            "execution_duration_sec": 8.0,
            "platform": {"os": "Windows"}
        }
        with open(os.path.join(results_dir, "experiment_manifest.json"), "w") as f:
            json.dump(manifest_data, f)

        with open(os.path.join(results_dir, "report.html"), "w") as f:
            f.write("<html><body>Report</body></html>")

        # Reset RepositoryManager singleton
        RepositoryManager._instance = None
        rm = RepositoryManager(workspace_dir=workspace_dir)
        rm.archive_experiment("exp-20260731T150000Z-api", source_results_dir=results_dir)

        app.state.repository_manager = rm
        app.state.workspace_dir = workspace_dir

        with TestClient(app) as client:
            yield client


def test_api_list_repository(api_client):
    response = api_client.get("/api/v1/repository")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["total"] >= 1

    exp = data["data"]["experiments"][0]
    assert exp["experiment_id"] == "exp-20260731T150000Z-api"
    assert exp["overall_verdict"] == "PASS"
    assert exp["git_commit"] == "c4d5e6f7"


def test_api_filter_repository(api_client):
    # Filter by PASS
    res1 = api_client.get("/api/v1/repository?verdict=PASS")
    assert res1.status_code == 200
    assert len(res1.json()["data"]["experiments"]) >= 1

    # Filter by FAIL
    res2 = api_client.get("/api/v1/repository?verdict=FAIL")
    assert res2.status_code == 200
    assert len(res2.json()["data"]["experiments"]) == 0

    # Filter by Scenario S3
    res3 = api_client.get("/api/v1/repository?scenario=S3")
    assert res3.status_code == 200
    assert len(res3.json()["data"]["experiments"]) >= 1


def test_api_get_repository_detail(api_client):
    response = api_client.get("/api/v1/repository/exp-20260731T150000Z-api")
    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["experiment_id"] == "exp-20260731T150000Z-api"
    assert detail["has_html_report"] is True


def test_api_get_repository_detail_not_found(api_client):
    response = api_client.get("/api/v1/repository/non-existent-id")
    assert response.status_code == 404
