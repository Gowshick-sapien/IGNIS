"""Integration tests for dashboard pages and report routes (Phase G2)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app

client = TestClient(app)


def test_experiments_page_route():
    res = client.get("/experiments")
    assert res.status_code == 200
    assert "Experiment Control Center" in res.text
    assert "Execution Parameters" in res.text


def test_reports_page_route():
    res = client.get("/reports")
    assert res.status_code == 200
    assert "Historical Report Browser" in res.text


def test_charts_page_route():
    res = client.get("/charts")
    assert res.status_code == 200
    assert "Interactive Chart Gallery" in res.text
    assert "plotly" in res.text.lower()


def test_reports_list_api():
    res = client.get("/api/v1/reports/list")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "reports" in data["data"]
