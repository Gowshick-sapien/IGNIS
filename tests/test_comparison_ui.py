"""Integration tests for Comparison UI page rendering (Phase G5)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_comparison_page_rendering(client):
    resp = client.get("/comparison")
    assert resp.status_code == 200
    assert "Experiment Comparison & Regression Analytics" in resp.text
    assert "Experiment A (Baseline)" in resp.text
    assert "Experiment B (Target)" in resp.text


def test_comparison_navbar_active_state(client):
    resp = client.get("/comparison")
    assert resp.status_code == 200
    assert 'href="/comparison" class="nav-link active"' in resp.text
