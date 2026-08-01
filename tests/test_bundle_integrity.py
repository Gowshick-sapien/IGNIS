"""Integrity tests for reproducibility bundle structure and SHA256 checksums (Phase G6)."""

import os
import json
import zipfile
import hashlib
import pytest
from src.cloud_dashboard.services.bundle_service import BundleService


class MockRepoManager:
    def get_experiment_detail(self, exp_id: str):
        if exp_id == "exp-integrity":
            return {
                "experiment_id": "exp-integrity",
                "directory": "2026-08-01_04-35-30_exp-integrity",
                "directory_path": os.path.abspath("results"),
                "timestamp": "2026-08-01T04:35:26Z",
                "overall_verdict": "PASS",
                "execution_duration_sec": 3.488,
                "seed": 4321,
                "trial_count": 5,
                "git_commit": "2b503f8",
                "platform_os": "Windows 11",
                "platform_python": "3.12.2",
                "scenarios": [
                    {"scenario_id": "S3", "verdict": "PASS", "duration_sec": 1.0}
                ]
            }
        return None


def test_bundle_extraction_integrity(tmp_path):
    repo = MockRepoManager()
    bundle_svc = BundleService(workspace_dir=str(tmp_path), repository_manager=repo)
    result = bundle_svc.build_bundle("exp-integrity")
    bundle_zip_path = result["bundle_path"]

    # Extract ZIP to temporary extraction directory
    extract_dir = tmp_path / "extracted_bundle"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(bundle_zip_path, "r") as zf:
        zf.extractall(extract_dir)

    root_items = os.listdir(extract_dir)
    assert len(root_items) == 1
    bundle_root = extract_dir / root_items[0]

    # Verify required root items
    assert (bundle_root / "bundle_manifest.json").exists()
    assert (bundle_root / "README.md").exists()

    # Verify required subdirectories
    assert (bundle_root / "report").exists()
    assert (bundle_root / "data").exists()
    assert (bundle_root / "environment").exists()
    assert (bundle_root / "scenarios").exists()

    # Verify environment metadata files
    assert (bundle_root / "environment" / "git_state.json").exists()
    assert (bundle_root / "environment" / "platform_metadata.json").exists()

    # Verify bundle_manifest.json SHA256 checksums
    manifest_path = bundle_root / "bundle_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        bundle_manifest = json.load(f)

    checksums = bundle_manifest.get("checksums", {})
    assert len(checksums) > 0

    # Verify extracted file checksums match manifest checksums
    for rel_path, expected_sha in checksums.items():
        if rel_path == "bundle_manifest.json":
            continue
        extracted_file_path = bundle_root / rel_path
        if extracted_file_path.exists():
            h = hashlib.sha256()
            with open(extracted_file_path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            calc_sha = h.hexdigest()
            assert calc_sha == expected_sha, f"SHA256 checksum mismatch for {rel_path}: expected {expected_sha}, calculated {calc_sha}"
