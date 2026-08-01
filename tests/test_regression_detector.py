"""Unit tests for RegressionDetector (Phase G5)."""

import os
import pytest
from src.cloud_dashboard.services.regression_detector import RegressionDetector


class MockRepoManager:
    def list_experiments(self, sort="timestamp", order="desc", page_size=100):
        exps = [
            {"experiment_id": "exp-2", "git_commit": "commit2", "timestamp": "2026-08-01T04:00:00Z"},
            {"experiment_id": "exp-1", "git_commit": "commit1", "timestamp": "2026-08-01T03:00:00Z"}
        ]
        return exps, len(exps)

    def get_experiment_detail(self, exp_id):
        if exp_id == "exp-1":
            return {
                "experiment_id": "exp-1",
                "overall_verdict": "PASS",
                "git_commit": "commit1",
                "platform_os": "Windows 11",
                "scenarios": [{"scenario_id": "S3", "verdict": "PASS"}],
                "metrics": {"scenario_results": {"S3": {"metrics": {"fog_decision_latency": {"mean": 0.5}}}}}
            }
        elif exp_id == "exp-2":
            return {
                "experiment_id": "exp-2",
                "overall_verdict": "PASS",
                "git_commit": "commit2",
                "platform_os": "Windows 11",
                "scenarios": [{"scenario_id": "S3", "verdict": "PASS"}],
                "metrics": {"scenario_results": {"S3": {"metrics": {"fog_decision_latency": {"mean": 0.7}}}}}
            }
        return None


def test_regression_detector_config_validation(tmp_path):
    detector = RegressionDetector(workspace_dir=str(tmp_path))
    rules_dir = tmp_path / "config"
    rules_dir.mkdir(parents=True, exist_ok=True)
    rules_file = rules_dir / "regression_rules.yaml"

    # Write valid rules YAML
    rules_file.write_text("""
rules:
  latency:
    metric_path: "scenario_results.S3.metrics.fog_decision_latency.mean"
    threshold_pct: 10
    direction: lower
""")

    validated = detector.validate_config(str(rules_file))
    assert "rules" in validated
    assert "latency" in validated["rules"]


def test_regression_detector_baseline_selection():
    repo = MockRepoManager()
    detector = RegressionDetector(repository_manager=repo)

    # 1. Matching commit strategy
    b_id, strat = detector.select_baseline_experiment("exp-curr", current_git_commit="commit1")
    assert b_id == "exp-1"
    assert strat == "SAME_COMMIT"

    # 2. Fallback to recent overall strategy
    b_id2, strat2 = detector.select_baseline_experiment("exp-curr", current_git_commit="commit_new")
    assert b_id2 == "exp-2"
    assert strat2 == "RECENT_OVERALL"
