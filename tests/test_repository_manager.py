"""Unit tests for RepositoryManager (Phase G4)."""

import os
import json
import sqlite3
import tempfile
import pytest

from src.cloud_dashboard.services.repository_manager import RepositoryManager


@pytest.fixture
def mock_repo_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = os.path.join(tmpdir, "workspace")
        results_dir = os.path.join(workspace_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        # Create dummy metrics.json
        metrics_data = {
            "overall_verdict": "PASS",
            "experiment_metadata": {
                "timestamp": "2026-07-31T14:00:00Z",
                "random_seed": 4321,
                "trial_count": 10,
                "total_duration_sec": 12.5,
                "regression_rules_hash": "abc123hash"
            },
            "scenario_results": {
                "S1": {
                    "verdict": "PASS",
                    "duration_sec": 5.2,
                    "trials_run": 10,
                    "metrics": {"fog_decision_latency": {"mean": 12.4, "ci_95_low": 10.1, "ci_95_high": 14.7}}
                },
                "S3": {
                    "verdict": "PASS",
                    "duration_sec": 7.3,
                    "trials_run": 10,
                    "metrics": {"fog_decision_latency": {"mean": 45.2, "ci_95_low": 40.0, "ci_95_high": 50.4}}
                }
            }
        }
        with open(os.path.join(results_dir, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump(metrics_data, f)

        # Create dummy experiment_manifest.json
        manifest_data = {
            "timestamp": "2026-07-31T14:00:00Z",
            "git_commit": "a1b2c3d4",
            "trial_count": 10,
            "random_seed": 4321,
            "execution_duration_sec": 12.5,
            "platform": {"os": "Windows 11", "python_version": "3.12.2", "hostname": "TEST-HOST"}
        }
        with open(os.path.join(results_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Create dummy report.md & report.html
        with open(os.path.join(results_dir, "report.md"), "w") as f:
            f.write("# Test Summary Report\n")
        with open(os.path.join(results_dir, "report.html"), "w") as f:
            f.write("<html><body><h1>Test HTML Report</h1></body></html>")

        # Reset singleton instance
        RepositoryManager._instance = None

        manager = RepositoryManager(workspace_dir=workspace_dir)
        yield manager, workspace_dir, results_dir


def test_repository_manager_archive_experiment(mock_repo_env):
    manager, workspace_dir, results_dir = mock_repo_env
    exp_id = "exp-20260731T140000Z-test"

    archived_path = manager.archive_experiment(exp_id, source_results_dir=results_dir)
    assert archived_path is not None
    assert os.path.exists(archived_path)
    assert os.path.exists(os.path.join(archived_path, "metrics.json"))
    assert os.path.exists(os.path.join(archived_path, "experiment_manifest.json"))
    assert os.path.exists(os.path.join(archived_path, "report.html"))

    # Verify SQLite index
    assert manager.is_experiment_archived(exp_id) is True

    detail = manager.get_experiment_detail(exp_id)
    assert detail is not None
    assert detail["experiment_id"] == exp_id
    assert detail["overall_verdict"] == "PASS"
    assert detail["git_commit"] == "a1b2c3d4"
    assert detail["trial_count"] == 10
    assert detail["archive_schema_version"] == "1.0"
    assert detail["manifest_sha256"] != "unknown_sha256"
    assert len(detail["scenarios"]) == 2


def test_repository_manager_immutability(mock_repo_env):
    manager, workspace_dir, results_dir = mock_repo_env
    exp_id = "exp-20260731T140000Z-immutable"

    path1 = manager.archive_experiment(exp_id, source_results_dir=results_dir)
    # Attempting second archival of same experiment ID returns original path without overwriting
    path2 = manager.archive_experiment(exp_id, source_results_dir=results_dir)
    assert path1 == path2


def test_repository_manager_query_and_filter(mock_repo_env):
    manager, workspace_dir, results_dir = mock_repo_env

    manager.archive_experiment("exp-1", source_results_dir=results_dir)
    experiments, total = manager.list_experiments(verdict="PASS")
    assert total >= 1
    assert experiments[0]["overall_verdict"] == "PASS"

    experiments_fail, total_fail = manager.list_experiments(verdict="FAIL")
    assert total_fail == 0
