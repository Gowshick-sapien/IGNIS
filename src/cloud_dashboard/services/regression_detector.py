"""IGNIS Automatic Regression Detector (Phase G5).

Evaluates completed experiments against configurable rule sets (config/regression_rules.yaml)
and historical baseline selection hierarchy (Same Commit -> Recent Overall -> Skip).
"""

import os
import json
import yaml
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any

from .repository_manager import RepositoryManager
from .comparison_service import ComparisonService
from ..schemas import ComparisonIndicator

logger = logging.getLogger("regression_detector")


class RegressionDetector:
    """Automatic regression analyzer evaluating completed experiments against configurable rules."""

    def __init__(self, workspace_dir: Optional[str] = None, repository_manager: Optional[RepositoryManager] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.rules_config_path = os.path.join(self.workspace_dir, "config", "regression_rules.yaml")
        self.repo_mgr = repository_manager or RepositoryManager(workspace_dir=self.workspace_dir)
        self.comparison_service = ComparisonService(repository_manager=self.repo_mgr)

    def validate_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Fail-fast validation of regression_rules.yaml at startup."""
        target_path = os.path.abspath(config_path or self.rules_config_path)
        if not os.path.exists(target_path):
            raise ValueError(f"Regression rules configuration file missing at: {target_path}")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse regression rules YAML at {target_path}: {e}")

        if not isinstance(data, dict) or "rules" not in data:
            raise ValueError(f"Invalid regression rules YAML: Root must contain 'rules' dictionary key.")

        rules = data.get("rules", {})
        if not isinstance(rules, dict):
            raise ValueError(f"Invalid regression rules YAML: 'rules' field must be a dictionary.")

        for rule_name, rule_def in rules.items():
            if not isinstance(rule_def, dict):
                raise ValueError(f"Rule '{rule_name}' must be a dictionary definition.")

            rule_type = rule_def.get("type")
            if rule_type == "verdict_transition":
                if "alert_on" not in rule_def:
                    raise ValueError(f"Verdict transition rule '{rule_name}' requires 'alert_on' specification.")
            else:
                if "metric_path" not in rule_def:
                    raise ValueError(f"Metric regression rule '{rule_name}' requires 'metric_path' field.")
                if "direction" not in rule_def or rule_def["direction"] not in ["lower", "higher"]:
                    raise ValueError(f"Metric rule '{rule_name}' requires direction 'lower' or 'higher'.")

        logger.info(f"Regression rules configuration validated successfully ({len(rules)} rules loaded).")
        return data

    def calculate_rules_hash(self) -> str:
        """Calculate SHA-256 hash of regression_rules.yaml for metadata tracking."""
        if not os.path.exists(self.rules_config_path):
            return "unknown_rules_hash"
        try:
            with open(self.rules_config_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return "error_rules_hash"

    def select_baseline_experiment(self, current_exp_id: str, current_git_commit: Optional[str] = None) -> Tuple[Optional[str], str]:
        """Select baseline experiment using explicit hierarchy:
        1. Most recent experiment with SAME Git commit
        2. Most recent experiment OVERALL
        3. None (Skip)
        """
        all_exps, total = self.repo_mgr.list_experiments(sort="timestamp", order="desc", page_size=100)
        # Exclude current experiment
        filtered = [e for e in all_exps if e.get("experiment_id") != current_exp_id]
        if not filtered:
            return None, "SKIPPED_NO_BASELINE"

        # 1. Check same Git commit match
        if current_git_commit and current_git_commit != "unknown":
            same_commit_exps = [e for e in filtered if e.get("git_commit") == current_git_commit]
            if same_commit_exps:
                baseline_id = same_commit_exps[0].get("experiment_id")
                logger.info(f"Selected baseline {baseline_id} matching current Git commit ({current_git_commit}).")
                return baseline_id, "SAME_COMMIT"

        # 2. Fallback to most recent overall
        recent_baseline_id = filtered[0].get("experiment_id")
        logger.info(f"Selected fallback baseline {recent_baseline_id} (most recent overall archive).")
        return recent_baseline_id, "RECENT_OVERALL"

    def detect_regressions(self, experiment_id: str, source_results_dir: Optional[str] = None) -> Dict[str, Any]:
        """Run regression detection for a target experiment against its baseline."""
        results_dir = os.path.abspath(source_results_dir or os.path.join(self.workspace_dir, "results"))
        metrics_path = os.path.join(results_dir, "metrics.json")
        rules_hash = self.calculate_rules_hash()

        current_commit = "unknown"
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                    current_commit = m_data.get("experiment_metadata", {}).get("git_commit", "unknown")
            except Exception:
                pass

        baseline_id, baseline_strategy = self.select_baseline_experiment(experiment_id, current_commit)

        if not baseline_id:
            summary = {
                "experiment_id": experiment_id,
                "baseline_experiment_id": None,
                "baseline_strategy": baseline_strategy,
                "regression_rules_hash": rules_hash,
                "status": "SKIPPED_NO_BASELINE",
                "total_regressions": 0,
                "regressions": [],
                "rule_evaluations": {}
            }
            self._save_regression_summary(experiment_id, summary, results_dir)
            return summary

        # Perform side-by-side comparison (Baseline A vs Current B)
        comp_result = self.comparison_service.compare(baseline_id, experiment_id)
        config_data = self.validate_config()
        rules = config_data.get("rules", {})

        regressions = []
        rule_evaluations = {}

        # Evaluate rules
        for rule_name, rule_def in rules.items():
            rule_type = rule_def.get("type")
            if rule_type == "verdict_transition":
                overall_a = comp_result["verdict_delta"]["overall_a"]
                overall_b = comp_result["verdict_delta"]["overall_b"]
                alert_on = rule_def.get("alert_on", "PASS_TO_FAIL")

                if alert_on == "PASS_TO_FAIL" and overall_a == "PASS" and overall_b == "FAIL":
                    reg = {
                        "rule": rule_name,
                        "type": "verdict_transition",
                        "baseline_value": overall_a,
                        "current_value": overall_b,
                        "message": f"Overall verdict regressed from {overall_a} to {overall_b}"
                    }
                    regressions.append(reg)
                    rule_evaluations[rule_name] = {"status": "REGRESSED", "details": reg["message"]}
                else:
                    rule_evaluations[rule_name] = {"status": "PASS", "details": f"{overall_a} -> {overall_b}"}
            else:
                # Metric path rule evaluation
                m_path = rule_def.get("metric_path", "")
                parts = m_path.split(".")
                # Expected path format: scenario_results.S3.metrics.fog_decision_latency.mean
                if len(parts) >= 4 and parts[0] == "scenario_results":
                    sid = parts[1]
                    m_name = parts[3]
                    thresh_pct = float(rule_def.get("threshold_pct", 10.0))
                    zero_tol = rule_def.get("zero_tolerance", False)
                    direction = rule_def.get("direction", "lower")

                    diff_entry = comp_result["metrics_diff"].get(sid, {}).get(m_name, {})
                    indicator = diff_entry.get("indicator")

                    if indicator == ComparisonIndicator.NOT_COMPARABLE.value:
                        rule_evaluations[rule_name] = {
                            "status": "NOT_COMPARABLE",
                            "details": f"Metric '{m_name}' missing in baseline or current experiment."
                        }
                    elif indicator == ComparisonIndicator.REGRESSED.value:
                        pct_chg = diff_entry.get("pct_change", 0.0)
                        mean_a = diff_entry.get("mean_a")
                        mean_b = diff_entry.get("mean_b")

                        is_regression = False
                        if zero_tol and (mean_a == 0.0 and mean_b > 0.0):
                            is_regression = True
                        elif abs(pct_chg) >= thresh_pct:
                            is_regression = True

                        if is_regression:
                            reg = {
                                "rule": rule_name,
                                "metric_name": m_name,
                                "scenario_id": sid,
                                "baseline_value": mean_a,
                                "current_value": mean_b,
                                "pct_change": pct_chg,
                                "message": f"{m_name} ({sid}) regressed: {mean_a} -> {mean_b} ({pct_chg:+.2f}%)"
                            }
                            regressions.append(reg)
                            rule_evaluations[rule_name] = {"status": "REGRESSED", "details": reg["message"]}
                        else:
                            rule_evaluations[rule_name] = {"status": "PASS", "details": f"Change within threshold ({pct_chg:.2f}%)"}
                    else:
                        rule_evaluations[rule_name] = {"status": "PASS", "details": diff_entry.get("details", "OK")}

        summary = {
            "experiment_id": experiment_id,
            "baseline_experiment_id": baseline_id,
            "baseline_strategy": baseline_strategy,
            "regression_rules_hash": rules_hash,
            "status": "REGRESSION_DETECTED" if len(regressions) > 0 else "NO_REGRESSION",
            "total_regressions": len(regressions),
            "regressions": regressions,
            "rule_evaluations": rule_evaluations
        }

        self._save_regression_summary(experiment_id, summary, results_dir)
        return summary

    def _save_regression_summary(self, experiment_id: str, summary: Dict[str, Any], results_dir: str) -> None:
        """Write regression_summary.json to active results and archived experiment repository folder."""
        # 1. Save to active results directory
        out_path = os.path.join(results_dir, "regression_summary.json")
        try:
            os.makedirs(results_dir, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Regression summary written to: {out_path}")
        except Exception as e:
            logger.error(f"Failed writing active regression_summary.json: {e}")

        # 2. Also copy directly to archived experiment folder if present
        try:
            archived_dir = self.repo_mgr.get_experiment_directory(experiment_id)
            if archived_dir and os.path.exists(archived_dir):
                repo_summary_path = os.path.join(archived_dir, "regression_summary.json")
                with open(repo_summary_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
                logger.info(f"Regression summary persisted to archived folder: {repo_summary_path}")
        except Exception as e:
            logger.warning(f"Could not persist regression summary to archive: {e}")
