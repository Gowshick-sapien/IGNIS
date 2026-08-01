"""Integration tests for Settings UI page rendering (Phase G6)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_settings_page_rendering(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "Settings & Export Preferences" in resp.text
    assert "Export Format Capabilities & Dependency Matrix" in resp.text
    assert "Quick Artifact Export & Publication Toolbar" in resp.text


def test_settings_navbar_active_state(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert 'href="/settings" class="nav-link active"' in resp.text
