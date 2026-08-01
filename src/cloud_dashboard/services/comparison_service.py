"""IGNIS Experiment Comparison Service (Phase G5).

Computes side-by-side metric diffs, verdict deltas, 95% CI overlap checks, statistical significance,
and environment diffs between historical experiment runs.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from ..schemas import ComparisonIndicator
from .repository_manager import RepositoryManager

logger = logging.getLogger("comparison_service")


class ComparisonService:
    """Service producing structured side-by-side comparisons between experiment runs."""

    # Metrics where LOWER numerical values indicate improved performance
    LOWER_IS_BETTER_METRICS = {
        "fog_decision_latency",
        "lateral_propagation_time",
        "false_positive_count",
        "message_loss_pct",
        "cross_talk_count"
    }

    # Metrics where HIGHER numerical values indicate improved performance
    HIGHER_IS_BETTER_METRICS = {
        "offline_continuity",
        "flush_success_rate",
        "is_clamped"
    }

    def __init__(self, repository_manager: Optional[RepositoryManager] = None):
        self.repo_mgr = repository_manager or RepositoryManager()

    def compare(self, exp_a_id: str, exp_b_id: str) -> Dict[str, Any]:
        """Perform full side-by-side comparison between experiment A and experiment B."""
        detail_a = self.repo_mgr.get_experiment_detail(exp_a_id)
        if not detail_a:
            raise ValueError(f"Experiment '{exp_a_id}' not found in repository.")

        detail_b = self.repo_mgr.get_experiment_detail(exp_b_id)
        if not detail_b:
            raise ValueError(f"Experiment '{exp_b_id}' not found in repository.")

        verdict_delta = self._compare_verdicts(detail_a, detail_b)
        metrics_diff = self._compare_metrics(detail_a, detail_b)
        environment_diff = self._compare_environments(detail_a, detail_b)

        return {
            "experiment_a": exp_a_id,
            "experiment_b": exp_b_id,
            "verdict_delta": verdict_delta,
            "metrics_diff": metrics_diff,
            "environment_diff": environment_diff
        }

    def _compare_verdicts(self, detail_a: Dict[str, Any], detail_b: Dict[str, Any]) -> Dict[str, Any]:
        overall_a = detail_a.get("overall_verdict", "UNKNOWN")
        overall_b = detail_b.get("overall_verdict", "UNKNOWN")
        changed = (overall_a != overall_b)

        scenarios_a = {s.get("scenario_id"): s.get("verdict", "UNKNOWN") for s in detail_a.get("scenarios", [])}
        scenarios_b = {s.get("scenario_id"): s.get("verdict", "UNKNOWN") for s in detail_b.get("scenarios", [])}

        all_scen_ids = sorted(list(set(scenarios_a.keys()) | set(scenarios_b.keys())))
        scen_diffs = {}
        for sid in all_scen_ids:
            v_a = scenarios_a.get(sid, "NOT_EXECUTED")
            v_b = scenarios_b.get(sid, "NOT_EXECUTED")
            if v_a == v_b:
                status = "UNCHANGED"
            elif v_a == "PASS" and v_b == "FAIL":
                status = "PASS_TO_FAIL"
            elif v_a == "FAIL" and v_b == "PASS":
                status = "FAIL_TO_PASS"
            else:
                status = f"{v_a}_TO_{v_b}"

            scen_diffs[sid] = {
                "verdict_a": v_a,
                "verdict_b": v_b,
                "status": status
            }

        return {
            "overall_a": overall_a,
            "overall_b": overall_b,
            "changed": changed,
            "scenarios": scen_diffs
        }

    def _compare_metrics(self, detail_a: Dict[str, Any], detail_b: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        metrics_a = detail_a.get("metrics", {}).get("scenario_results", {})
        metrics_b = detail_b.get("metrics", {}).get("scenario_results", {})

        all_sids = sorted(list(set(metrics_a.keys()) | set(metrics_b.keys())))
        result_diffs = {}

        for sid in all_sids:
            scen_a = metrics_a.get(sid, {}).get("metrics", {})
            scen_b = metrics_b.get(sid, {}).get("metrics", {})

            all_metric_names = sorted(list(set(scen_a.keys()) | set(scen_b.keys())))
            sid_diffs = {}

            for m_name in all_metric_names:
                struct_a = scen_a.get(m_name)
                struct_b = scen_b.get(m_name)

                # Missing metric handling -> NOT_COMPARABLE
                if struct_a is None or struct_b is None:
                    sid_diffs[m_name] = {
                        "mean_a": self._extract_mean(struct_a),
                        "mean_b": self._extract_mean(struct_b),
                        "ci_a": self._extract_ci(struct_a),
                        "ci_b": self._extract_ci(struct_b),
                        "ci_overlap": None,
                        "significant_difference": None,
                        "delta": None,
                        "pct_change": None,
                        "indicator": ComparisonIndicator.NOT_COMPARABLE.value,
                        "details": "Metric missing in one or both experiment runs."
                    }
                    continue

                val_a = self._extract_mean(struct_a)
                val_b = self._extract_mean(struct_b)
                ci_a = self._extract_ci(struct_a)
                ci_b = self._extract_ci(struct_b)

                if val_a is None or val_b is None:
                    sid_diffs[m_name] = {
                        "mean_a": val_a,
                        "mean_b": val_b,
                        "ci_a": ci_a,
                        "ci_b": ci_b,
                        "ci_overlap": None,
                        "significant_difference": None,
                        "delta": None,
                        "pct_change": None,
                        "indicator": ComparisonIndicator.NOT_COMPARABLE.value,
                        "details": "Non-numeric metric values cannot be compared numerically."
                    }
                    continue

                delta = round(val_b - val_a, 4)
                pct_change = round((delta / val_a * 100.0), 2) if val_a != 0 else 0.0

                # Check 95% Confidence Interval overlap
                ci_overlap = None
                significant_diff = False
                if ci_a and ci_b and len(ci_a) >= 2 and len(ci_b) >= 2:
                    ci_overlap = max(ci_a[0], ci_b[0]) <= min(ci_a[1], ci_b[1])
                    significant_diff = not ci_overlap and abs(pct_change) >= 5.0

                # Determine comparison indicator
                indicator = self._determine_indicator(m_name, delta, pct_change, val_a)

                sid_diffs[m_name] = {
                    "mean_a": val_a,
                    "mean_b": val_b,
                    "ci_a": ci_a,
                    "ci_b": ci_b,
                    "ci_overlap": ci_overlap,
                    "significant_difference": significant_diff,
                    "delta": delta,
                    "pct_change": pct_change,
                    "indicator": indicator.value,
                    "details": f"Delta: {delta:+.4f} ({pct_change:+.2f}%)"
                }

            result_diffs[sid] = sid_diffs

        return result_diffs

    def _determine_indicator(self, metric_name: str, delta: float, pct_change: float, val_a: float) -> ComparisonIndicator:
        if abs(delta) < 1e-6:
            return ComparisonIndicator.UNCHANGED
        if val_a != 0.0 and abs(pct_change) < 1.0:
            return ComparisonIndicator.UNCHANGED

        if metric_name in self.LOWER_IS_BETTER_METRICS:
            return ComparisonIndicator.IMPROVED if delta < 0 else ComparisonIndicator.REGRESSED
        elif metric_name in self.HIGHER_IS_BETTER_METRICS:
            return ComparisonIndicator.IMPROVED if delta > 0 else ComparisonIndicator.REGRESSED
        else:
            # Default for unknown metrics: lower is better
            return ComparisonIndicator.IMPROVED if delta < 0 else ComparisonIndicator.REGRESSED

    def _extract_mean(self, val_struct: Any) -> Optional[float]:
        if isinstance(val_struct, dict):
            if "mean" in val_struct and isinstance(val_struct["mean"], (int, float)):
                return float(val_struct["mean"])
            if "value" in val_struct and isinstance(val_struct["value"], (int, float)):
                return float(val_struct["value"])
        elif isinstance(val_struct, (int, float)):
            return float(val_struct)
        return None

    def _extract_ci(self, val_struct: Any) -> Optional[List[float]]:
        if isinstance(val_struct, dict):
            ci = val_struct.get("confidence95")
            if isinstance(ci, (list, tuple)) and len(ci) >= 2:
                return [round(float(ci[0]), 4), round(float(ci[1]), 4)]
        return None

    def _compare_environments(self, detail_a: Dict[str, Any], detail_b: Dict[str, Any]) -> Dict[str, Any]:
        commit_a = detail_a.get("git_commit", "unknown")
        commit_b = detail_b.get("git_commit", "unknown")
        os_a = detail_a.get("platform_os", "unknown")
        os_b = detail_b.get("platform_os", "unknown")
        py_a = detail_a.get("platform_python", "unknown")
        py_b = detail_b.get("platform_python", "unknown")

        return {
            "os_match": (os_a == os_b),
            "python_match": (py_a == py_b),
            "git_commit_a": commit_a,
            "git_commit_b": commit_b,
            "same_commit": (commit_a == commit_b)
        }
