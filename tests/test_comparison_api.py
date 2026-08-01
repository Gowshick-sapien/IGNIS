"""Integration tests for Comparison REST API routes (Phase G5)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app
from src.cloud_dashboard.services.comparison_service import ComparisonService


class MockRepoMgr:
    def get_experiment_detail(self, exp_id: str):
        if exp_id in ("exp-a", "exp-b"):
            return {
                "experiment_id": exp_id,
                "overall_verdict": "PASS",
                "git_commit": "2b503f8",
                "platform_os": "Windows 11",
                "platform_python": "3.12.2",
                "scenarios": [{"scenario_id": "S3", "verdict": "PASS"}],
                "metrics": {
                    "scenario_results": {
                        "S3": {
                            "metrics": {
                                "fog_decision_latency": {"mean": 0.5}
                            }
                        }
                    }
                }
            }
        return None


from src.cloud_dashboard.routes.comparison import get_comparison_service


@pytest.fixture
def client():
    cs = ComparisonService(repository_manager=MockRepoMgr())
    app.dependency_overrides[get_comparison_service] = lambda: cs
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_compare_endpoint(client):
    resp = client.get("/api/v1/experiments/compare?a=exp-a&b=exp-b")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["experiment_a"] == "exp-a"
    assert data["data"]["experiment_b"] == "exp-b"


def test_compare_summary_endpoint(client):
    resp = client.get("/api/v1/experiments/compare/summary?a=exp-a&b=exp-b")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "verdict_delta" in data["data"]


def test_compare_not_found_endpoint(client):
    resp = client.get("/api/v1/experiments/compare?a=exp-a&b=exp-missing")
    assert resp.status_code == 404
