"""IGNIS Reproducibility Bundle Service (Phase G6).

Compiles complete self-contained research reproduction packages containing raw data, metrics, manifests,
environment snapshots, scenario definitions, methodology docs, Git commit/diff snapshots,
and tamper-verifiable bundle_manifest.json SHA256 checksums.
"""

import os
import json
import shutil
import glob
import hashlib
import zipfile
import subprocess
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .repository_manager import RepositoryManager

logger = logging.getLogger("bundle_service")


class BundleService:
    """Service building complete reproducibility bundles for experiment runs."""

    def __init__(self, workspace_dir: Optional[str] = None, repository_manager: Optional[RepositoryManager] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.repo_mgr = repository_manager or RepositoryManager(workspace_dir=self.workspace_dir)
        self.bundle_export_dir = os.path.join(self.workspace_dir, "reports", "exports")
        os.makedirs(self.bundle_export_dir, exist_ok=True)

    def _file_sha256(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return "file_not_found"
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _capture_git_state(self) -> Dict[str, Any]:
        """Capture git branch, commit hash, commit message, status, and uncommitted diff."""
        git_info = {
            "git_commit": "unknown",
            "branch": "unknown",
            "commit_message": "unknown",
            "is_clean": True,
            "status_output": "",
            "uncommitted_diff": ""
        }
        try:
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.workspace_dir, timeout=1.0, text=True).strip()
            git_info["git_commit"] = commit
        except Exception:
            pass

        try:
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=self.workspace_dir, timeout=1.0, text=True).strip()
            git_info["branch"] = branch
        except Exception:
            pass

        try:
            msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], cwd=self.workspace_dir, timeout=1.0, text=True).strip()
            git_info["commit_message"] = msg
        except Exception:
            pass

        try:
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.workspace_dir, timeout=1.0, text=True).strip()
            git_info["status_output"] = status
            git_info["is_clean"] = (len(status) == 0)
        except Exception:
            pass

        try:
            diff = subprocess.check_output(["git", "diff"], cwd=self.workspace_dir, timeout=1.0, text=True).strip()
            git_info["uncommitted_diff"] = diff[:5000] # Limit size
        except Exception:
            pass

        return git_info

    def build_bundle(self, experiment_id: str) -> Dict[str, Any]:
        """Build/overwrite a reproducibility bundle ZIP archive for an experiment."""
        detail = self.repo_mgr.get_experiment_detail(experiment_id)
        if not detail:
            raise ValueError(f"Experiment '{experiment_id}' not found in repository.")

        exp_dir = detail["directory_path"]
        staging_dir = os.path.join(self.bundle_export_dir, f".staging_bundle_{experiment_id}")
        zip_output_path = os.path.join(self.bundle_export_dir, f"reproducibility_bundle_{experiment_id}.zip")

        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)

        os.makedirs(staging_dir, exist_ok=True)
        bundle_root = os.path.join(staging_dir, f"reproducibility_bundle_{experiment_id}")
        os.makedirs(bundle_root, exist_ok=True)

        # Create subdirectories
        dir_report = os.path.join(bundle_root, "report")
        dir_charts = os.path.join(bundle_root, "charts")
        dir_data = os.path.join(bundle_root, "data")
        dir_env = os.path.join(bundle_root, "environment")
        dir_scen = os.path.join(bundle_root, "scenarios")
        dir_logs = os.path.join(bundle_root, "logs")
        dir_method = os.path.join(bundle_root, "methodology")

        for d in (dir_report, dir_charts, dir_data, dir_env, dir_scen, dir_logs, dir_method):
            os.makedirs(d, exist_ok=True)

        # 1. Populate data/
        for fname in ("metrics.json", "raw_results.json", "experiment_manifest.json", "regression_summary.json", "progress_events.jsonl"):
            src = os.path.join(exp_dir, fname)
            if not os.path.exists(src):
                src = os.path.join(self.workspace_dir, "results", fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dir_data, fname))

        # 2. Populate report/
        for rname in ("report.md", "report.html"):
            src = os.path.join(exp_dir, rname)
            if not os.path.exists(src):
                src = os.path.join(self.workspace_dir, "results", rname)
            if os.path.exists(src):
                out_name = "project_results_report.md" if rname == "report.md" else rname
                shutil.copy2(src, os.path.join(dir_report, out_name))

        # 3. Populate charts/
        charts_src = os.path.join(exp_dir, "charts")
        if not os.path.exists(charts_src):
            charts_src = os.path.join(self.workspace_dir, "results", "charts")
        if os.path.exists(charts_src):
            for png in glob.glob(os.path.join(charts_src, "*.png")):
                shutil.copy2(png, dir_charts)

        # 4. Populate environment/
        # 4. Populate environment/
        req_file = os.path.join(self.workspace_dir, "requirements.txt")
        if not os.path.exists(req_file):
            req_file = os.path.join(os.getcwd(), "requirements.txt")
        if os.path.exists(req_file):
            shutil.copy2(req_file, os.path.join(dir_env, "requirements.txt"))

        compose_file = os.path.join(self.workspace_dir, "docker-compose.yml")
        if not os.path.exists(compose_file):
            compose_file = os.path.join(os.getcwd(), "docker-compose.yml")
        if os.path.exists(compose_file):
            shutil.copy2(compose_file, os.path.join(dir_env, "docker-compose.yml"))

        plat_meta = {
            "platform_os": detail.get("platform_os"),
            "platform_python": detail.get("platform_python"),
            "platform_docker": detail.get("platform_docker"),
            "hostname": detail.get("hostname")
        }
        with open(os.path.join(dir_env, "platform_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(plat_meta, f, indent=2)

        git_state = self._capture_git_state()
        with open(os.path.join(dir_env, "git_state.json"), "w", encoding="utf-8") as f:
            json.dump(git_state, f, indent=2)

        # 5. Populate scenarios/
        scen_src = os.path.join(self.workspace_dir, "scenarios")
        if not os.path.exists(scen_src):
            scen_src = os.path.join(os.getcwd(), "scenarios")
        if os.path.exists(scen_src):
            for yaml_f in glob.glob(os.path.join(scen_src, "*.yaml")):
                shutil.copy2(yaml_f, dir_scen)

        # 6. Populate logs/
        log_src = os.path.join(exp_dir, "logs", "experiment.log")
        if not os.path.exists(log_src):
            log_src = os.path.join(self.workspace_dir, "results", "logs", "experiment.log")
        if os.path.exists(log_src):
            shutil.copy2(log_src, os.path.join(dir_logs, "experiment.log"))

        # 7. Populate methodology/
        arch_doc = os.path.join(self.workspace_dir, "docs", "architecture.md")
        if not os.path.exists(arch_doc):
            arch_doc = os.path.join(os.getcwd(), "docs", "architecture.md")
        if os.path.exists(arch_doc):
            shutil.copy2(arch_doc, os.path.join(dir_method, "architecture.md"))

        regr_rules = os.path.join(self.workspace_dir, "config", "regression_rules.yaml")
        if not os.path.exists(regr_rules):
            regr_rules = os.path.join(os.getcwd(), "config", "regression_rules.yaml")
        if os.path.exists(regr_rules):
            shutil.copy2(regr_rules, os.path.join(dir_method, "regression_rules.yaml"))

        # Compute SHA256 checksums for bundle_manifest.json
        checksums = {}
        for root, _, files in os.walk(bundle_root):
            for file in files:
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, bundle_root).replace("\\", "/")
                checksums[rel_p] = self._file_sha256(abs_p)

        bundle_manifest = {
            "bundle_version": "1.0.0",
            "bundle_time": datetime.now(timezone.utc).isoformat(),
            "experiment_id": experiment_id,
            "bundle_generator_version": "phase-g-6.0",
            "checksums": checksums
        }

        manifest_file = os.path.join(bundle_root, "bundle_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(bundle_manifest, f, indent=2)

        # Add manifest file itself to checksums list
        checksums["bundle_manifest.json"] = self._file_sha256(manifest_file)

        # Generate README.md
        readme_content = f"""# IGNIS Research Reproducibility Bundle

**Experiment ID**: `{experiment_id}`  
**Overall Verdict**: `{detail.get('overall_verdict')}`  
**Git Commit**: `{detail.get('git_commit')}`  
**Trial Count**: `{detail.get('trial_count')}`  
**Execution Duration**: `{detail.get('execution_duration_sec')} seconds`  

---

## 1. System & Environment Requirements
- **Python Version**: {detail.get('platform_python', '3.12+')}
- **Operating System**: {detail.get('platform_os', 'Windows / Linux')}
- **Docker Version**: {detail.get('platform_docker', 'Docker Compose v2')}
- **Required Container Images**:
  - `python:3.11-slim` (fog-node, edge-sim)
  - `eclipse-mosquitto:2` (mqtt-broker)
  - `influxdb:2.7` (influxdb time-series)

---

## 2. How to Reproduce Results
1. Install Python dependencies: `pip install -r environment/requirements.txt`
2. Start background container services: `docker compose up -d`
3. Execute deterministic scenario replay:
   ```bash
   python -m src.run_experiment --trials {detail.get('trial_count', 5)} --seed {detail.get('seed', 4321)}
   ```
4. Verify generated outputs against `data/metrics.json` and `report/report.html`.

---

## 3. Core Artifact SHA256 Checksums
| File | SHA256 Hash |
|---|---|
| `data/metrics.json` | `{checksums.get('data/metrics.json', 'N/A')}` |
| `data/raw_results.json` | `{checksums.get('data/raw_results.json', 'N/A')}` |
| `data/experiment_manifest.json` | `{checksums.get('data/experiment_manifest.json', 'N/A')}` |
| `report/report.html` | `{checksums.get('report/report.html', 'N/A')}` |
| `report/project_results_report.md` | `{checksums.get('report/project_results_report.md', 'N/A')}` |
"""

        with open(os.path.join(bundle_root, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)

        # Create final bundle ZIP file
        if os.path.exists(zip_output_path):
            os.remove(zip_output_path)

        with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(bundle_root):
                for d in dirs:
                    abs_d = os.path.join(root, d)
                    rel_d = os.path.relpath(abs_d, staging_dir).replace("\\", "/") + "/"
                    zf.writestr(rel_d, "")
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, staging_dir)
                    zf.write(full_p, arcname=rel_p)

        # Clean staging directory
        shutil.rmtree(staging_dir, ignore_errors=True)

        file_size = os.path.getsize(zip_output_path)
        zip_hash = self._file_sha256(zip_output_path)

        logger.info(f"Reproducibility bundle created for {experiment_id} at {zip_output_path} ({file_size} bytes, sha256: {zip_hash[:8]})")

        return {
            "experiment_id": experiment_id,
            "bundle_path": zip_output_path,
            "file_size_bytes": file_size,
            "sha256_hash": zip_hash,
            "manifest": bundle_manifest
        }
