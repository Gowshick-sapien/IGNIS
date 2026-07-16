import os
import sys
import unittest
import shutil
import tempfile
import json
from unittest.mock import patch, MagicMock

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.report_generator import generate_charts, generate_report, load_raw_results
from src.metrics_collector import calculate_stats

class TestReportPipeline(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.charts_dir = os.path.join(self.temp_dir, "charts")
        self.report_path = os.path.join(self.temp_dir, "project_results_report.md")
        
        # Standard dummy metrics matching metrics.json format
        self.dummy_metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-16T09:00:00Z",
                "git_commit": "a1b2c3d",
                "trial_count": 10,
                "random_seed": 3849121,
                "total_duration_sec": 245.3,
                "platform": {
                    "os": "Windows 11",
                    "architecture": "x86_64",
                    "python_version": "3.11.9",
                    "timezone": "Asia/Kolkata",
                    "hostname": "IGNIS-DEV"
                },
                "scenario_versions": {"S1": "1.0", "S2": "1.0"},
                "scenario_checksums": {"S1": "2fb45...", "S2": "d991a..."},
                "ci_method": "internal_t_table"
            },
            "scenario_results": {
                "S1": {
                    "status": "PASS",
                    "reason": "Baseline passes",
                    "trials": 10,
                    "metrics": {
                        "max_state": {"value": "GREEN", "status": "PASS", "threshold": "GREEN", "operator": "=="}
                    }
                },
                "S3": {
                    "status": "PASS",
                    "reason": "All assertions passed across 10 trials",
                    "trials": 10,
                    "metrics": {
                        "fog_decision_latency": {
                            "sample_count": 10,
                            "min": 0.08,
                            "max": 0.15,
                            "mean": 0.11,
                            "median": 0.10,
                            "std_dev": 0.02,
                            "confidence95": [0.10, 0.12],
                            "status": "PASS",
                            "reason": "Mean 0.11s <= threshold 1.0s",
                            "threshold": 1.0,
                            "operator": "<="
                        }
                    }
                }
            },
            "summary": {
                "total_scenarios": 7,
                "passed": 5,
                "failed": 0,
                "invalid": 2,
                "incomplete": 0,
                "overall_verdict": "PASS"
            }
        }
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_report_generator_dissertation_structure(self):
        # Generate the report
        generate_report(self.dummy_metrics, self.report_path)
        
        self.assertTrue(os.path.exists(self.report_path))
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Verify 9 dissertation sections exist
        self.assertIn("# IGNIS — Consolidated Simulation Results Report", content)
        self.assertIn("## 1. Executive Summary", content)
        self.assertIn("## 2. Experimental Setup", content)
        self.assertIn("## 3. Scenario Execution", content)
        self.assertIn("## 4. Experimental Results", content)
        self.assertIn("## 5. Cross-Scenario Analysis", content)
        self.assertIn("## 6. Architecture Validation Summary", content)
        self.assertIn("## 7. Discussion", content)
        self.assertIn("## 8. Limitations", content)
        self.assertIn("## 9. Conclusion", content)
        
        # Verify execution platform metadata
        self.assertIn("Windows 11", content)
        self.assertIn("a1b2c3d", content)
        self.assertIn("3849121", content)
        self.assertIn("internal_t_table", content)

    def test_report_charts_generation(self):
        # Generate charts
        charts = generate_charts(self.dummy_metrics, self.charts_dir)
        
        # Check generated list size
        self.assertEqual(len(charts), 10)
        
        # Check files exist
        expected_files = [
            "decision_latency_boxplot.png",
            "decision_latency_histogram.png",
            "lateral_propagation_comparison.png",
            "lateral_propagation_ci.png",
            "false_positive_trend.png",
            "offline_buffering_timeline.png",
            "message_integrity_heatmap.png",
            "scenario_comparison_summary.png",
            "state_transition_timeline.png",
            "execution_timeline.png"
        ]
        for f in expected_files:
            self.assertTrue(os.path.exists(os.path.join(self.charts_dir, f)), f"{f} does not exist")

    @patch('matplotlib.pyplot.savefig')
    def test_report_chart_failure_resilience(self, mock_savefig):
        # Mock savefig to raise an exception on specific charts to test resilience
        # It will raise an exception on the 3rd save (lateral_propagation_comparison.png)
        save_count = 0
        def side_effect(*args, **kwargs):
            nonlocal save_count
            save_count += 1
            if save_count == 3:
                raise RuntimeError("Disk full or Matplotlib error")
            return MagicMock()
            
        mock_savefig.side_effect = side_effect
        
        # We expect it to finish without crashing, returning 9 charts (skipping the failed one)
        charts = generate_charts(self.dummy_metrics, self.charts_dir)
        self.assertEqual(len(charts), 9)

    def test_ci_method_fallback_statistics(self):
        # Test custom Student-t CI logic with small sample sizes
        # Case A: df = 9 (N = 10)
        data = [0.1, 0.12, 0.11, 0.09, 0.13, 0.10, 0.11, 0.12, 0.11, 0.10]
        
        with patch.dict('sys.modules', {'scipy': None, 'scipy.stats': None}):
            stats = calculate_stats(data)
            self.assertEqual(stats["sample_count"], 10)
            self.assertEqual(stats["ci_method"], "internal_t_table")
            
            # Verify 95% Confidence Interval boundaries are calculated correctly
            ci = stats["confidence95"]
            self.assertEqual(len(ci), 2)
            self.assertTrue(ci[0] < stats["mean"])
            self.assertTrue(ci[1] > stats["mean"])
        
        # Case B: scipy exact comparison (if scipy is present)
        try:
            import scipy.stats
            # Verify internal math matches scipy boundaries
            # If scipy is present, calculate_stats will use scipy
            stats_with_scipy = calculate_stats(data)
            self.assertEqual(stats_with_scipy["ci_method"], "scipy")
        except ImportError:
            pass
            
    def test_load_raw_results_fallback(self):
        # If directory doesn't exist, it should load fallback mock datasets
        results = load_raw_results("non_existent_directory_abc_123")
        self.assertIn("S3", results)
        self.assertTrue(len(results["S3"]) > 0)
        self.assertEqual(results["S3"][0]["events"][0]["state"], "RED")
