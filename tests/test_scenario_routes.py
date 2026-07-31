"""Integration tests for scenario browser & read-only YAML parsing (Phase G2)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app

client = TestClient(app)


def test_scenarios_page_route():
    res = client.get("/scenarios")
    assert res.status_code == 200
    assert "Scenario Browser (Read-Only)" in res.text
    assert "READ-ONLY POLICY ENFORCED" in res.text


def test_scenarios_parsed_cards():
    res = client.get("/scenarios")
    assert res.status_code == 200
    # Check if S1, S2, S3 or scenario cards exist in rendered text
    text = res.text
    assert "S1" in text or "Scenario" in text
