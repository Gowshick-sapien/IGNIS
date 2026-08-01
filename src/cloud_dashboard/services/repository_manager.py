"""IGNIS Experiment Repository Manager (Phase G4).

Sole writer service managing atomic directory archival into experiment_repository/ and SQLite metadata indexing.
"""

import os
import json
import shutil
import sqlite3
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from .repository_migrations import RepositoryMigrations

logger = logging.getLogger("repository_manager")


class RepositoryManager:
    """Singleton manager serving as the sole writer for experiment_repository/ and metadata.db."""

    _instance: Optional["RepositoryManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(RepositoryManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, workspace_dir: Optional[str] = None):
        with self._instance_lock:
            if workspace_dir:
                self.workspace_dir = os.path.abspath(workspace_dir)
                self.repo_dir = os.path.join(self.workspace_dir, "experiment_repository")
                self.db_path = os.path.join(self.repo_dir, "metadata.db")

            if getattr(self, "_initialized", False):
                return

            if not hasattr(self, "workspace_dir"):
                self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
                self.repo_dir = os.path.join(self.workspace_dir, "experiment_repository")
                self.db_path = os.path.join(self.repo_dir, "metadata.db")

            os.makedirs(self.repo_dir, exist_ok=True)
            self._migrations = RepositoryMigrations()
            self._migrations.migrate(self.db_path)

            self._initialized = True
            logger.info(f"RepositoryManager singleton initialized. Repo: {self.repo_dir}")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _calculate_file_sha256(self, filepath: str) -> str:
        """Calculate SHA-256 digest of a target file."""
        if not os.path.exists(filepath):
            return "unknown_sha256"
        hasher = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating SHA256 for {filepath}: {e}")
            return "error_sha256"

    def is_experiment_archived(self, experiment_id: str) -> bool:
        """Check if an experiment_id is already present in metadata.db."""
        if not os.path.exists(self.db_path):
            return False
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM experiments WHERE experiment_id = ?;", (experiment_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def archive_experiment(self, experiment_id: str, source_results_dir: Optional[str] = None) -> Optional[str]:
        """Atomically archive active results from source_results_dir to experiment_repository/."""
        src_dir = os.path.abspath(source_results_dir or os.path.join(self.workspace_dir, "results"))
        if not os.path.exists(src_dir):
            logger.warning(f"Cannot archive experiment {experiment_id}: Source directory {src_dir} does not exist.")
            return None

        # Check immutability policy: if already archived, return existing path
        if self.is_experiment_archived(experiment_id):
            logger.info(f"Experiment {experiment_id} is already archived in metadata.db (immutability policy enforced).")
            return self.get_experiment_directory(experiment_id)

        now_utc = datetime.now(timezone.utc)
        ts_folder_prefix = now_utc.strftime("%Y-%m-%d_%H-%M-%S")
        target_dir_name = f"{ts_folder_prefix}_{experiment_id}"
        final_target_dir = os.path.join(self.repo_dir, target_dir_name)
        staging_dir = os.path.join(self.repo_dir, f".tmp_{experiment_id}")

        logger.info(f"Starting atomic archival for experiment {experiment_id} into staging: {staging_dir}")

        try:
            # 1. Atomic Staging Copy
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
            os.makedirs(staging_dir, exist_ok=True)

            for item in os.listdir(src_dir):
                s_path = os.path.join(src_dir, item)
                d_path = os.path.join(staging_dir, item)
                if os.path.isfile(s_path):
                    shutil.copy2(s_path, d_path)
                elif os.path.isdir(s_path):
                    shutil.copytree(s_path, d_path)

            # 2. Verify staging artifacts & compute manifest_sha256
            manifest_path = os.path.join(staging_dir, "experiment_manifest.json")
            metrics_path = os.path.join(staging_dir, "metrics.json")
            manifest_sha256 = self._calculate_file_sha256(manifest_path)

            # Load metrics and manifest data
            metrics_data = {}
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        metrics_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read metrics.json during archival: {e}")

            manifest_data = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read experiment_manifest.json during archival: {e}")

            # 3. Atomic Rename from staging to final directory
            if os.path.exists(final_target_dir):
                shutil.rmtree(final_target_dir)
            os.rename(staging_dir, final_target_dir)
            logger.info(f"Atomically renamed staging folder to final archive: {final_target_dir}")

            # 4. Insert Metadata into SQLite with explicit Transaction Boundaries
            archived_at_str = now_utc.isoformat()
            exp_meta = metrics_data.get("experiment_metadata", {})
            summary_data = metrics_data.get("summary", {})
            overall_verdict = summary_data.get("overall_verdict", metrics_data.get("overall_verdict", "INVALID"))
            trial_count = manifest_data.get("trial_count", exp_meta.get("trial_count", 0))
            seed = manifest_data.get("random_seed", exp_meta.get("random_seed", 4321))
            git_commit = manifest_data.get("git_commit", "unknown")
            duration_sec = manifest_data.get("execution_duration_sec", exp_meta.get("total_duration_sec", 0.0))
            platform_info = manifest_data.get("platform", exp_meta.get("platform", {}))

            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION;")
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO experiments (
                        experiment_id, directory, timestamp, archived_at, seed, git_commit,
                        trial_count, overall_verdict, execution_duration_sec, platform_os,
                        platform_python, platform_docker, hostname, regression_rules_hash,
                        manifest_sha256, archive_schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    experiment_id,
                    target_dir_name,
                    exp_meta.get("timestamp", archived_at_str),
                    archived_at_str,
                    seed,
                    git_commit,
                    trial_count,
                    overall_verdict,
                    duration_sec,
                    platform_info.get("os", "unknown"),
                    platform_info.get("python_version", "unknown"),
                    platform_info.get("docker_version", "unknown"),
                    platform_info.get("hostname", "unknown"),
                    exp_meta.get("regression_rules_hash", ""),
                    manifest_sha256,
                    "1.0"
                ))

                # Insert scenario records
                scenario_results = metrics_data.get("scenario_results", {})
                for sid, sdata in scenario_results.items():
                    s_verdict = sdata.get("status", sdata.get("verdict", "INVALID"))
                    s_dur = sdata.get("duration_sec", 0.0)
                    s_trials = sdata.get("trials", sdata.get("trials_run", sdata.get("trial_count", 0)))
                    
                    # Extract Fog Decision Latency statistics if present
                    lat_metric = sdata.get("metrics", {}).get("fog_decision_latency", {})
                    l_mean = lat_metric.get("mean")
                    ci_bounds = lat_metric.get("confidence95", [])
                    if isinstance(ci_bounds, (list, tuple)) and len(ci_bounds) >= 2:
                        l_ci_low = ci_bounds[0]
                        l_ci_high = ci_bounds[1]
                    else:
                        l_ci_low = lat_metric.get("ci_95_low")
                        l_ci_high = lat_metric.get("ci_95_high")

                    cursor.execute("""
                        INSERT INTO experiment_scenarios (
                            experiment_id, scenario_id, verdict, duration_sec, trial_count,
                            latency_mean, latency_ci_low, latency_ci_high
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        experiment_id, sid, s_verdict, s_dur, s_trials, l_mean, l_ci_low, l_ci_high
                    ))

                conn.commit()
                logger.info(f"SQLite metadata indexed successfully for experiment {experiment_id}.")
                return final_target_dir
            except Exception as db_err:
                conn.rollback()
                logger.error(f"SQLite insertion failed for experiment {experiment_id}, rolling back transaction: {db_err}")
                raise db_err
            finally:
                conn.close()

        except Exception as err:
            logger.error(f"Error archiving experiment {experiment_id}: {err}")
            if os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir)
                except Exception:
                    pass
            raise err

    def get_experiment_directory(self, experiment_id: str) -> Optional[str]:
        """Fetch absolute path to archived directory for an experiment_id."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT directory FROM experiments WHERE experiment_id = ?;", (experiment_id,))
            row = cursor.fetchone()
            if row:
                return os.path.join(self.repo_dir, row["directory"])
            return None
        finally:
            conn.close()

    def list_experiments(
        self,
        verdict: Optional[str] = None,
        scenario: Optional[str] = None,
        commit: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort: str = "timestamp",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query historical experiments with filtering, sorting, and pagination (READ ONLY)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            where_clauses = []
            params = []

            if verdict:
                where_clauses.append("e.overall_verdict = ?")
                params.append(verdict.upper())

            if scenario:
                where_clauses.append("e.experiment_id IN (SELECT DISTINCT experiment_id FROM experiment_scenarios WHERE scenario_id = ?)")
                params.append(scenario.upper())

            if commit:
                where_clauses.append("e.git_commit LIKE ?")
                params.append(f"{commit}%")

            if from_date:
                where_clauses.append("e.timestamp >= ?")
                params.append(from_date)

            if to_date:
                where_clauses.append("e.timestamp <= ?")
                params.append(to_date)

            where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Count total query records
            count_sql = f"SELECT COUNT(*) FROM experiments e {where_str};"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]

            # Validate sort column
            sort_map = {
                "timestamp": "e.timestamp",
                "verdict": "e.overall_verdict",
                "duration": "e.execution_duration_sec",
                "trials": "e.trial_count"
            }
            sort_col = sort_map.get(sort.lower(), "e.timestamp")
            sort_dir = "DESC" if order.lower() == "desc" else "ASC"

            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT e.* FROM experiments e
                {where_str}
                ORDER BY {sort_col} {sort_dir}
                LIMIT ? OFFSET ?;
            """
            cursor.execute(query_sql, params + [page_size, offset])
            exp_rows = cursor.fetchall()

            results = []
            exp_map = {}
            exp_ids = []
            for row in exp_rows:
                exp_dict = dict(row)
                exp_id = exp_dict["experiment_id"]
                exp_dict["scenarios_summary"] = []
                results.append(exp_dict)
                exp_map[exp_id] = exp_dict
                exp_ids.append(exp_id)

            if exp_ids:
                placeholders = ",".join("?" for _ in exp_ids)
                scen_sql = f"""
                    SELECT experiment_id, scenario_id, verdict, duration_sec, trial_count, latency_mean, latency_ci_low, latency_ci_high
                    FROM experiment_scenarios
                    WHERE experiment_id IN ({placeholders})
                    ORDER BY scenario_id ASC;
                """
                cursor.execute(scen_sql, exp_ids)
                for srow in cursor.fetchall():
                    sdict = dict(srow)
                    eid = sdict.pop("experiment_id")
                    if eid in exp_map:
                        exp_map[eid]["scenarios_summary"].append(sdict)

            return results, total_count
        finally:
            conn.close()

    def get_experiment_detail(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for an experiment_id (READ ONLY)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE experiment_id = ?;", (experiment_id,))
            row = cursor.fetchone()
            if not row:
                return None

            detail = dict(row)
            dir_path = os.path.join(self.repo_dir, detail["directory"])
            detail["directory_path"] = dir_path

            # Fetch scenario rows
            cursor.execute("SELECT * FROM experiment_scenarios WHERE experiment_id = ? ORDER BY scenario_id ASC;", (experiment_id,))
            detail["scenarios"] = [dict(s) for s in cursor.fetchall()]

            # Load metrics.json if present
            metrics_path = os.path.join(dir_path, "metrics.json")
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        detail["metrics"] = json.load(f)
                except Exception:
                    detail["metrics"] = {}

            # Load manifest if present
            manifest_path = os.path.join(dir_path, "experiment_manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        detail["manifest"] = json.load(f)
                except Exception:
                    detail["manifest"] = {}

            detail["has_html_report"] = os.path.exists(os.path.join(dir_path, "report.html"))
            detail["has_md_report"] = os.path.exists(os.path.join(dir_path, "report.md"))
            
            charts_dir = os.path.join(dir_path, "charts")
            detail["charts"] = os.listdir(charts_dir) if os.path.exists(charts_dir) else []

            return detail
        finally:
            conn.close()
