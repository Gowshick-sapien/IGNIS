"""Unit tests for ExportService (Phase G6)."""

import os
import pytest
from src.cloud_dashboard.services.export_service import ExportService


class MockRepoManager:
    def get_experiment_detail(self, exp_id: str):
        if exp_id == "exp-valid":
            return {
                "experiment_id": "exp-valid",
                "directory": "2026-08-01_04-35-30_exp-valid",
                "directory_path": os.path.abspath("results"),
                "timestamp": "2026-08-01T04:35:26Z",
                "overall_verdict": "PASS",
                "execution_duration_sec": 3.488,
                "git_commit": "2b503f8",
                "platform_os": "Windows 11",
                "platform_python": "3.12.2",
                "scenarios": [
                    {"scenario_id": "S3", "verdict": "PASS", "duration_sec": 1.0, "trial_count": 5, "latency_mean": 0.5}
                ],
                "metrics": {
                    "scenario_results": {
                        "S3": {
                            "metrics": {
                                "fog_decision_latency": {"mean": 0.5, "confidence95": [0.4, 0.6]}
                            }
                        }
                    }
                }
            }
        return None


def test_export_service_format_capabilities():
    exp_svc = ExportService(repository_manager=MockRepoManager())
    caps = exp_svc.get_format_capabilities()

    assert "available" in caps
    assert "md" in caps["available"]
    assert "html" in caps["available"]
    assert "csv" in caps["available"]
    assert "json" in caps["available"]
    assert "zip" in caps["available"]
    assert "optional_status" in caps


def test_export_service_formats(tmp_path):
    repo = MockRepoManager()
    exp_svc = ExportService(workspace_dir=str(tmp_path), repository_manager=repo)

    # Test Markdown export
    md_path = exp_svc.export("exp-valid", "md")
    assert os.path.exists(md_path)
    assert md_path.endswith(".md")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "EXPORT METADATA" in content
        assert "exp-valid" in content

    # Test HTML export
    html_path = exp_svc.export("exp-valid", "html")
    assert os.path.exists(html_path)
    assert html_path.endswith(".html")

    # Test CSV export
    csv_path = exp_svc.export("exp-valid", "csv")
    assert os.path.exists(csv_path)
    assert csv_path.endswith(".csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()
        assert "IGNIS EXPORT METADATA" in csv_content
        assert "fog_decision_latency" in csv_content

    # Test JSON export
    json_path = exp_svc.export("exp-valid", "json")
    assert os.path.exists(json_path)
    assert json_path.endswith(".json")

    # Test ZIP export
    zip_path = exp_svc.export("exp-valid", "zip")
    assert os.path.exists(zip_path)
    assert zip_path.endswith(".zip")


def test_export_service_invalid_format():
    repo = MockRepoManager()
    exp_svc = ExportService(repository_manager=repo)
    with pytest.raises(ValueError):
        exp_svc.export("exp-valid", "invalid_fmt")
