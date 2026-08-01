import unittest
import tempfile
import os
import json
from src.report_generator import generate_report
from src.metrics_collector import calculate_stats

class TestReportConsistency(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.report_path = os.path.join(self.test_dir.name, "project_results_report.md")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_all_pass_execution(self):
        # Test 1: Mock metrics where all scenarios PASS
        metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-18T12:00:00Z",
                "git_commit": "abcdef123456",
                "trial_count": 10,
                "random_seed": 42,
                "total_duration_sec": 45.2,
                "platform": {"os": "Linux", "architecture": "x86_64", "python_version": "3.10.0", "timezone": "UTC", "hostname": "test-host"},
                "scenario_versions": {"S1": "1.0", "S2": "1.0", "S3": "1.0", "S4": "1.0", "S5": "1.0", "S6": "1.0", "S7": "1.0"},
                "scenario_checksums": {"S1": "sum1", "S2": "sum2", "S3": "sum3", "S4": "sum4", "S5": "sum5", "S6": "sum6", "S7": "sum7"},
                "ci_method": "t_table"
            },
            "scenario_results": {
                "S1": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {}},
                "S2": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {}},
                "S3": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"fog_decision_latency": {"mean": 0.15, "minimum": 0.05, "maximum": 0.35, "median": 0.14, "std_dev": 0.05, "confidence95": [0.12, 0.18], "status": "PASS"}}},
                "S4": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"false_positive_count": {"mean": 0.0, "minimum": 0.0, "maximum": 0.0, "median": 0.0, "std_dev": 0.0, "confidence95": [0.0, 0.0], "status": "PASS"}}},
                "S5": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"offline_continuity": {"mean": 1.0, "minimum": 1.0, "maximum": 1.0, "median": 1.0, "std_dev": 0.0, "confidence95": [1.0, 1.0], "status": "PASS"}}},
                "S6": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"lateral_propagation_time": {"mean": 3.5, "minimum": 2.1, "maximum": 4.9, "median": 3.4, "std_dev": 0.4, "confidence95": [3.2, 3.8], "status": "PASS"}}},
                "S7": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"cross_talk_count": {"mean": 0.0, "minimum": 0.0, "maximum": 0.0, "median": 0.0, "std_dev": 0.0, "confidence95": [0.0, 0.0], "status": "PASS"}}}
            },
            "summary": {
                "total_scenarios": 7,
                "passed": 7,
                "failed": 0,
                "invalid": 0,
                "incomplete": 0,
                "overall_verdict": "PASS"
            }
        }
        
        generate_report(metrics, self.report_path)
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("Overall Verdict**: **PASS**", content)
        self.assertIn("7 scenarios successfully satisfied all assertions.", content)
        self.assertIn("0 scenarios failed assertion checks.", content)
        self.assertIn("0 scenarios could not be evaluated", content)
        self.assertIn("[PASS] Validated", content)
        self.assertNotIn("[FAIL] Validation Failed", content)
        self.assertNotIn(" Not Validated", content)
        self.assertIn("All core architecture claims are fully validated by empirical data", content)

    def test_all_fail_execution(self):
        # Test 2: Mock metrics where all scenarios FAIL
        metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-18T12:00:00Z",
                "git_commit": "abcdef123456",
                "trial_count": 10,
                "random_seed": 42,
                "total_duration_sec": 45.2,
                "platform": {"os": "Linux", "architecture": "x86_64", "python_version": "3.10.0", "timezone": "UTC", "hostname": "test-host"},
                "scenario_versions": {"S1": "1.0", "S2": "1.0", "S3": "1.0", "S4": "1.0", "S5": "1.0", "S6": "1.0", "S7": "1.0"},
                "scenario_checksums": {"S1": "sum1", "S2": "sum2", "S3": "sum3", "S4": "sum4", "S5": "sum5", "S6": "sum6", "S7": "sum7"},
                "ci_method": "t_table"
            },
            "scenario_results": {
                "S1": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {}},
                "S2": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {}},
                "S3": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"fog_decision_latency": {"mean": 1.25, "minimum": 0.95, "maximum": 1.55, "median": 1.24, "std_dev": 0.15, "confidence95": [1.12, 1.38], "status": "FAIL"}}},
                "S4": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"false_positive_count": {"mean": 1.0, "minimum": 0.0, "maximum": 1.0, "median": 1.0, "std_dev": 0.0, "confidence95": [1.0, 1.0], "status": "FAIL"}}},
                "S5": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"offline_continuity": {"mean": 0.0, "minimum": 0.0, "maximum": 0.0, "median": 0.0, "std_dev": 0.0, "confidence95": [0.0, 0.0], "status": "FAIL"}}},
                "S6": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"lateral_propagation_time": {"mean": 12.5, "minimum": 10.1, "maximum": 14.9, "median": 12.4, "std_dev": 1.4, "confidence95": [11.2, 13.8], "status": "FAIL"}}},
                "S7": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"cross_talk_count": {"mean": 5.0, "minimum": 2.0, "maximum": 8.0, "median": 5.0, "std_dev": 1.0, "confidence95": [4.2, 5.8], "status": "FAIL"}}}
            },
            "summary": {
                "total_scenarios": 7,
                "passed": 0,
                "failed": 7,
                "invalid": 0,
                "incomplete": 0,
                "overall_verdict": "FAIL"
            }
        }
        
        generate_report(metrics, self.report_path)
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("Overall Verdict**: **FAIL**", content)
        self.assertIn("7 scenarios failed assertion checks.", content)
        self.assertIn("[FAIL] Validation Failed", content)
        self.assertNotIn("[PASS] Validated", content)
        self.assertIn("Additional implementation work is required before the architecture can be considered fully validated", content)

    def test_mixed_execution(self):
        # Test 3: Mixed execution status (some PASS, FAIL, INVALID)
        metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-18T12:00:00Z",
                "git_commit": "abcdef123456",
                "trial_count": 10,
                "random_seed": 42,
                "total_duration_sec": 45.2,
                "platform": {"os": "Linux", "architecture": "x86_64", "python_version": "3.10.0", "timezone": "UTC", "hostname": "test-host"},
                "scenario_versions": {"S1": "1.0", "S2": "1.0", "S3": "1.0", "S4": "1.0", "S5": "1.0", "S6": "1.0", "S7": "1.0"},
                "scenario_checksums": {"S1": "sum1", "S2": "sum2", "S3": "sum3", "S4": "sum4", "S5": "sum5", "S6": "sum6", "S7": "sum7"},
                "ci_method": "t_table"
            },
            "scenario_results": {
                "S1": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {}},
                "S2": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {}},
                "S3": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"fog_decision_latency": {"mean": 0.15, "minimum": 0.05, "maximum": 0.35, "median": 0.14, "std_dev": 0.05, "confidence95": [0.12, 0.18], "status": "PASS"}}},
                "S4": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"false_positive_count": {"mean": 1.0, "minimum": 0.0, "maximum": 1.0, "median": 1.0, "std_dev": 0.0, "confidence95": [1.0, 1.0], "status": "FAIL"}}},
                "S5": {"trials": 10, "status": "FAIL", "reason": "Assertion failed", "metrics": {"offline_continuity": {"mean": 0.0, "minimum": 0.0, "maximum": 0.0, "median": 0.0, "std_dev": 0.0, "confidence95": [0.0, 0.0], "status": "FAIL"}}},
                "S6": {"trials": 10, "status": "INVALID", "reason": "Required events were unavailable", "metrics": {"lateral_propagation_time": {"status": "INVALID", "reason": "No events found"}}},
                "S7": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"cross_talk_count": {"mean": 0.0, "minimum": 0.0, "maximum": 0.0, "median": 0.0, "std_dev": 0.0, "confidence95": [0.0, 0.0], "status": "PASS"}}}
            },
            "summary": {
                "total_scenarios": 7,
                "passed": 4,
                "failed": 2,
                "invalid": 1,
                "incomplete": 0,
                "overall_verdict": "FAIL"
            }
        }
        
        generate_report(metrics, self.report_path)
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("Overall Verdict**: **FAIL**", content)
        self.assertIn("4 scenarios successfully satisfied all assertions.", content)
        self.assertIn("2 scenarios failed assertion checks.", content)
        self.assertIn("1 scenario could not be evaluated", content)
        self.assertIn("[PASS] Validated", content)
        self.assertIn("[FAIL] Validation Failed", content)
        self.assertIn(" Not Validated", content)

    def test_all_invalid_execution(self):
        # Test 4: All INVALID scenarios (specifically metric unavailable display)
        metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-18T12:00:00Z",
                "git_commit": "abcdef123456",
                "trial_count": 10,
                "random_seed": 42,
                "total_duration_sec": 45.2,
                "platform": {"os": "Linux", "architecture": "x86_64", "python_version": "3.10.0", "timezone": "UTC", "hostname": "test-host"},
                "scenario_versions": {"S1": "1.0", "S2": "1.0", "S3": "1.0", "S4": "1.0", "S5": "1.0", "S6": "1.0", "S7": "1.0"},
                "scenario_checksums": {"S1": "sum1", "S2": "sum2", "S3": "sum3", "S4": "sum4", "S5": "sum5", "S6": "sum6", "S7": "sum7"},
                "ci_method": "t_table"
            },
            "scenario_results": {
                "S1": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {}},
                "S2": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {}},
                "S3": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {"fog_decision_latency": {"status": "INVALID", "reason": "No events found"}}},
                "S4": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {"false_positive_count": {"status": "INVALID", "reason": "No events found"}}},
                "S5": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {"offline_continuity": {"status": "INVALID", "reason": "No events found"}}},
                "S6": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {"lateral_propagation_time": {"status": "INVALID", "reason": "No events found"}}},
                "S7": {"trials": 10, "status": "INVALID", "reason": "No events", "metrics": {"cross_talk_count": {"status": "INVALID", "reason": "No events found"}}}
            },
            "summary": {
                "total_scenarios": 7,
                "passed": 0,
                "failed": 0,
                "invalid": 7,
                "incomplete": 0,
                "overall_verdict": "INVALID"
            }
        }
        
        generate_report(metrics, self.report_path)
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("Overall Verdict**: **INVALID**", content)
        self.assertIn("Metric unavailable", content)
        self.assertIn(" Not Validated", content)

    def test_deterministic_replay(self):
        # Test 5: Two mocked executions using the same seed producing identical outcomes, metrics, report contents
        data = [1.2, 1.4, 1.3, 1.5, 1.4, 1.6, 1.2, 1.3, 1.4, 1.5]
        
        # We verify calculate_stats is fully deterministic on the same input
        import random
        random.seed(9999)
        stats1 = calculate_stats(data)
        
        random.seed(9999)
        stats2 = calculate_stats(data)
        
        self.assertEqual(stats1, stats2)
        
        # Verify generate_report is deterministic given the same metrics dict
        metrics = {
            "experiment_metadata": {
                "timestamp": "2026-07-18T12:00:00Z",
                "git_commit": "abcdef123456",
                "trial_count": 10,
                "random_seed": 42,
                "total_duration_sec": 45.2,
                "platform": {"os": "Linux", "architecture": "x86_64", "python_version": "3.10.0", "timezone": "UTC", "hostname": "test-host"},
                "scenario_versions": {"S1": "1.0", "S2": "1.0", "S3": "1.0", "S4": "1.0", "S5": "1.0", "S6": "1.0", "S7": "1.0"},
                "scenario_checksums": {"S1": "sum1", "S2": "sum2", "S3": "sum3", "S4": "sum4", "S5": "sum5", "S6": "sum6", "S7": "sum7"},
                "ci_method": "t_table"
            },
            "scenario_results": {
                "S3": {"trials": 10, "status": "PASS", "reason": "All assertions passed", "metrics": {"fog_decision_latency": stats1}}
            },
            "summary": {
                "total_scenarios": 1,
                "passed": 1,
                "failed": 0,
                "invalid": 0,
                "incomplete": 0,
                "overall_verdict": "PASS"
            }
        }
        
        report_path1 = os.path.join(self.test_dir.name, "report1.md")
        report_path2 = os.path.join(self.test_dir.name, "report2.md")
        
        generate_report(metrics, report_path1)
        generate_report(metrics, report_path2)
        
        with open(report_path1, "r", encoding="utf-8") as f:
            content1 = f.read()
        with open(report_path2, "r", encoding="utf-8") as f:
            content2 = f.read()
            
        self.assertEqual(content1, content2)

if __name__ == "__main__":
    unittest.main()
