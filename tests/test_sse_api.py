"""Integration tests for GET /api/v1/experiment/stream SSE endpoint (Phase G3)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app
from src.cloud_dashboard.services.process_manager import ProcessManager

client = TestClient(app)


def test_sse_stream_headers():
    pm = ProcessManager()
    pm.reporter.reset("exp-test-sse")
    pm._experiment_id = "exp-test-sse"
    pm.reporter.emit_experiment_complete(overall_verdict="PASS", duration_sec=1.0)

    with client.stream("GET", "/api/v1/experiment/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        for line in response.iter_lines():
            assert line is not None
            break
