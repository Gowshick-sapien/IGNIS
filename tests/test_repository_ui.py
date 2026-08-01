"""Integration tests for Repository UI template rendering (Phase G4)."""

import tempfile
import os
import pytest
from fastapi.testclient import TestClient

from src.cloud_dashboard.app import app
from src.cloud_dashboard.services.repository_manager import RepositoryManager


@pytest.fixture
def ui_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        RepositoryManager._instance = None
        rm = RepositoryManager(workspace_dir=tmpdir)
        app.state.repository_manager = rm
        app.state.workspace_dir = tmpdir

        with TestClient(app) as client:
            yield client


def test_repository_ui_page_rendering(ui_client):
    response = ui_client.get("/repository")
    assert response.status_code == 200
    html = response.text

    assert "Historical Experiment Repository" in html
    assert "filter-verdict" in html
    assert "filter-scenario" in html
    assert "filter-commit" in html
    assert "repository-list-container" in html


def test_repository_navbar_active_state(ui_client):
    response = ui_client.get("/repository")
    assert response.status_code == 200
    html = response.text

    # Navbar link for Repository must have active class
    assert 'href="/repository" class="nav-link active"' in html
