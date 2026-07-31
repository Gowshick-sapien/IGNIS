"""Integration tests for live UI EventSource scripts and progress bar DOM elements (Phase G3)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app

client = TestClient(app)


def test_experiments_ui_sse_elements():
    res = client.get("/experiments")
    assert res.status_code == 200
    text = res.text

    # Verify SSE progress bar elements
    assert "progress-bar-container" in text
    assert "progress-bar-fill" in text
    assert "info-eta" in text
    assert "info-trial-counter" in text
    assert "info-active-scenario" in text

    # Verify native EventSource JS integration and graceful closure
    assert "EventSource('/api/v1/experiment/stream')" in text
    assert "addEventListener('EXPERIMENT_STARTED'" in text
    assert "addEventListener('TRIAL_PROGRESS'" in text
    assert "addEventListener('EXPERIMENT_COMPLETE'" in text
    assert "closeEventSource()" in text
