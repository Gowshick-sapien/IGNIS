"""Unit tests for ComparisonService (Phase G5)."""

import pytest
from src.cloud_dashboard.services.comparison_service import ComparisonService
from src.cloud_dashboard.schemas import ComparisonIndicator


class MockRepositoryManager:
    def get_experiment_detail(self, exp_id: str):
        if exp_id == "exp-1":
            return {
                "experiment_id": "exp-1",
                "overall_verdict": "PASS",
                "git_commit": "abc1234",
                "platform_os": "Windows 11",
                "platform_python": "3.12.2",
                "scenarios": [
                    {"scenario_id": "S3", "verdict": "PASS", "duration_sec": 1.0}
                ],
                "metrics": {
                    "scenario_results": {
                        "S3": {
                            "metrics": {
                                "fog_decision_latency": {"mean": 0.50, "confidence95": [0.40, 0.60]},
                                "false_positive_count": {"mean": 0.0}
                            }
                        }
                    }
                }
            }
        elif exp_id == "exp-2":
            return {
                "experiment_id": "exp-2",
                "overall_verdict": "PASS",
                "git_commit": "abc1234",
                "platform_os": "Windows 11",
                "platform_python": "3.12.2",
                "scenarios": [
                    {"scenario_id": "S3", "verdict": "PASS", "duration_sec": 1.0}
                ],
                "metrics": {
                    "scenario_results": {
                        "S3": {
                            "metrics": {
                                "fog_decision_latency": {"mean": 0.40, "confidence95": [0.30, 0.50]},
                                "false_positive_count": {"mean": 2.0}
                            }
                        }
                    }
                }
            }
        return None


def test_comparison_service_valid():
    repo = MockRepositoryManager()
    cs = ComparisonService(repository_manager=repo)
    result = cs.compare("exp-1", "exp-2")

    assert result["experiment_a"] == "exp-1"
    assert result["experiment_b"] == "exp-2"
    assert result["verdict_delta"]["changed"] is False

    diff_s3 = result["metrics_diff"]["S3"]
    # Decision latency decreased from 0.50 to 0.40 -> IMPROVED
    assert diff_s3["fog_decision_latency"]["indicator"] == ComparisonIndicator.IMPROVED.value
    # False positives increased from 0.0 to 2.0 -> REGRESSED
    assert diff_s3["false_positive_count"]["indicator"] == ComparisonIndicator.REGRESSED.value

    assert result["environment_diff"]["same_commit"] is True


def test_comparison_service_missing_experiment():
    repo = MockRepositoryManager()
    cs = ComparisonService(repository_manager=repo)
    with pytest.raises(ValueError):
        cs.compare("exp-1", "exp-missing")
