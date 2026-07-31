"""
Integration & Unit tests for HTML Report Generator & Metric Classification (Phase G1)
"""

import os
import json
import tempfile
import unittest
from src.cloud_dashboard.reporting.html_generator import (
    generate_html_report,
    ReportGenerationError
)
from src.cloud_dashboard.reporting.templates import (
    render_metric_card,
    format_float,
    format_confidence_interval
)


class TestHTMLGenerator(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = self.tmp_dir.name

        self.metrics_file = os.path.join(tmp_path, "metrics.json")
        self.raw_file = os.path.join(tmp_path, "raw_results.json")
        self.manifest_file = os.path.join(tmp_path, "experiment_manifest.json")
        self.output_file = os.path.join(tmp_path, "report.html")

        metrics_data = {
            "overall_verdict": "PASS",
            "total_trials": 10,
            "total_scenarios": 7,
            "passed_scenarios": 7,
            "total_execution_duration_sec": 15.2,
            "scenario_results": {
                "S1": {
                    "name": "Normal Operations",
                    "status": "PASS",
                    "trials": 10,
                    "execution_duration_sec": 1.1,
                    "reason": "All assertions passed across 1 rules",
                    "metrics": {
                        "max_state": {"value": "GREEN", "status": "PASS", "threshold": "GREEN", "operator": "=="}
                    }
                },
                "S3": {
                    "name": "Hazardous Condition",
                    "status": "FAIL",
                    "trials": 10,
                    "execution_duration_sec": 1.5,
                    "reason": "Assertions failed: No matching events found",
                    "metrics": {
                        "fog_decision_latency": {"status": "INVALID", "reason": "No matching events found"},
                        "final_state": {"value": "GREEN", "status": "FAIL", "threshold": "RED", "operator": "=="}
                    }
                },
                "S4": {
                    "name": "False Positive Immunity",
                    "status": "FAIL",
                    "trials": 10,
                    "execution_duration_sec": 1.0,
                    "reason": "Assertions failed",
                    "metrics": {
                        "false_positive_count": {
                            "sample_count": 10, "mean": 0.0, "median": 0.0, "std_dev": 0.0,
                            "confidence95": [0.0, 0.0], "status": "PASS", "reason": "Mean 0.0000 == threshold 0"
                        }
                    }
                }
            }
        }

        raw_data = {
            "S1": [{"duration_sec": 1.1}],
            "S3": [{"events": [{"sensor_timestamp": "2026-07-16T09:02:00.000Z", "decision_timestamp": "2026-07-16T09:02:00.120Z"}]}]
        }

        manifest_data = {
            "experiment_id": "exp-20260724T090000Z-a1b2",
            "timestamp": "2026-07-24T09:00:00Z",
            "git_commit": "a1b2c3d4e5f6",
            "git_branch": "main",
            "seed": 42,
            "environment": {
                "python_version": "3.12.0",
                "os_platform": "Windows-11"
            }
        }

        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f)
        with open(self.raw_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f)
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_generate_html_report_success(self):
        res_path = generate_html_report(
            metrics_path=self.metrics_file,
            raw_results_path=self.raw_file,
            manifest_path=self.manifest_file,
            output_path=self.output_file,
            theme="dark"
        )

        self.assertTrue(os.path.exists(res_path))
        with open(res_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Assert self-contained HTML structure & key deterministic IDs
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn('<body data-theme="dark">', html_content)
        self.assertIn('id="summary"', html_content)
        self.assertIn('id="key-findings"', html_content)
        self.assertIn('id="scenario-s1"', html_content)
        self.assertIn('id="scenario-s3"', html_content)
        self.assertIn('id="chart-decision-latency"', html_content)
        self.assertIn('Statistical Metric', html_content)
        self.assertIn('Assertion Metric', html_content)
        self.assertIn('Invalid / Unavailable', html_content)

    def test_metric_classification_type_1(self):
        stat_metric = {
            "mean": 3.2456,
            "median": 3.200,
            "std_dev": 0.123,
            "confidence95": [3.100, 3.390],
            "sample_count": 10,
            "status": "PASS",
            "reason": "Mean 3.246 <= threshold 5.0"
        }
        card_html = render_metric_card("lateral_propagation_time", stat_metric)
        self.assertIn("Statistical Metric", card_html)
        self.assertIn("3.246", card_html)
        self.assertIn("3.200", card_html)
        self.assertIn("0.123", card_html)
        self.assertIn("[3.100, 3.390]", card_html)

    def test_metric_classification_type_2(self):
        assert_metric = {
            "value": "GREEN",
            "threshold": "GREEN",
            "operator": "==",
            "status": "PASS",
            "reason": "GREEN == threshold GREEN"
        }
        card_html = render_metric_card("max_state", assert_metric)
        self.assertIn("Assertion Metric", card_html)
        self.assertIn("GREEN", card_html)
        self.assertNotIn("Mean", card_html)
        self.assertNotIn("Confidence Interval", card_html)

    def test_metric_classification_type_3(self):
        invalid_metric = {
            "status": "INVALID",
            "reason": "No matching events found"
        }
        card_html = render_metric_card("fog_decision_latency", invalid_metric)
        self.assertIn("Invalid / Unavailable", card_html)
        self.assertIn("No matching events found", card_html)
        self.assertNotIn("Mean", card_html)

    def test_generate_html_report_missing_file_raises_error(self):
        with self.assertRaises(ReportGenerationError):
            generate_html_report(
                metrics_path="nonexistent.json",
                raw_results_path=self.raw_file,
                manifest_path=self.manifest_file,
                output_path=self.output_file
            )


if __name__ == "__main__":
    unittest.main()
