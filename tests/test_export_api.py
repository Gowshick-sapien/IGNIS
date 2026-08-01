"""Integration tests for Export & Reproducibility REST API routes (Phase G6)."""

import os
import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app
from src.cloud_dashboard.routes.export_routes import get_result_manager
from src.cloud_dashboard.services.result_manager import ResultManager
from src.cloud_dashboard.services.export_service import ExportService
from src.cloud_dashboard.services.bundle_service import BundleService


class MockRepoMgr:
    def get_experiment_detail(self, exp_id: str):
        if exp_id in ("exp-export-1", "exp-export-2"):
            return {
                "experiment_id": exp_id,
                "directory": "2026-08-01_04-35-30_exp-export",
                "directory_path": os.path.abspath("results"),
                "timestamp": "2026-08-01T04:35:26Z",
                "overall_verdict": "PASS",
                "execution_duration_sec": 3.488,
                "git_commit": "2b503f8",
                "scenarios": [{"scenario_id": "S3", "verdict": "PASS"}]
            }
        return None


@pytest.fixture
def client(tmp_path):
    repo = MockRepoMgr()
    exp_svc = ExportService(workspace_dir=str(tmp_path), repository_manager=repo)
    bun_svc = BundleService(workspace_dir=str(tmp_path), repository_manager=repo)
    rm = ResultManager(export_service=exp_svc, bundle_service=bun_svc)

    app.dependency_overrides[get_result_manager] = lambda: rm
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_export_formats_endpoint(client):
    resp = client.get("/api/v1/experiment/export/formats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "available" in data["data"]


def test_export_file_endpoint(client):
    resp = client.get("/api/v1/experiment/export/exp-export-1?format=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]


def test_export_not_found_endpoint(client):
    resp = client.get("/api/v1/experiment/export/nonexistent-exp?format=csv")
    assert resp.status_code == 404


def test_reproduce_bundle_endpoint(client):
    resp = client.post("/api/v1/experiment/exp-export-1/reproduce")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["experiment_id"] == "exp-export-1"
