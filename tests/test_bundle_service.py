"""Unit tests for BundleService (Phase G6)."""

import os
import json
import pytest
from src.cloud_dashboard.services.bundle_service import BundleService


class MockRepoManager:
    def get_experiment_detail(self, exp_id: str):
        if exp_id == "exp-bundle":
            return {
                "experiment_id": "exp-bundle",
                "directory": "2026-08-01_04-35-30_exp-bundle",
                "directory_path": os.path.abspath("results"),
                "timestamp": "2026-08-01T04:35:26Z",
                "overall_verdict": "PASS",
                "execution_duration_sec": 3.488,
                "seed": 4321,
                "trial_count": 5,
                "git_commit": "2b503f8",
                "platform_os": "Windows 11",
                "scenarios": [
                    {"scenario_id": "S3", "verdict": "PASS", "duration_sec": 1.0, "trial_count": 5, "latency_mean": 0.5}
                ]
            }
        return None


def test_bundle_service_build_bundle(tmp_path):
    repo = MockRepoManager()
    bundle_svc = BundleService(workspace_dir=str(tmp_path), repository_manager=repo)
    result = bundle_svc.build_bundle("exp-bundle")

    assert result["experiment_id"] == "exp-bundle"
    assert os.path.exists(result["bundle_path"])
    assert result["file_size_bytes"] > 0
    assert "sha256_hash" in result
    assert "manifest" in result

    manifest = result["manifest"]
    assert manifest["experiment_id"] == "exp-bundle"
    assert manifest["bundle_version"] == "1.0.0"
    assert "checksums" in manifest


def test_bundle_service_invalid_experiment():
    repo = MockRepoManager()
    bundle_svc = BundleService(repository_manager=repo)
    with pytest.raises(ValueError):
        bundle_svc.build_bundle("exp-nonexistent")
