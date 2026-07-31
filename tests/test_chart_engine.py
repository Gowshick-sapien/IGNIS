"""
Unit tests for Plotly Chart Engine (Phase G1)
"""

import unittest
from src.cloud_dashboard.reporting.chart_engine import ChartEngine


class TestChartEngine(unittest.TestCase):

    def setUp(self):
        self.mock_metrics = {
            "overall_verdict": "PASS",
            "total_trials": 10,
            "total_scenarios": 7,
            "passed_scenarios": 7,
            "total_execution_duration_sec": 12.5,
            "scenario_results": {
                "S3": {"metrics": {"fog_decision_latency": {"mean": 0.12, "ci_95_lower": 0.10, "ci_95_upper": 0.14}}},
                "S6": {"metrics": {"lateral_propagation_time": {"mean": 3.4, "ci_95_lower": 3.2, "ci_95_upper": 3.6}}},
                "S4": {"metrics": {"false_positive_count": {"mean": 0}}},
                "S5": {"metrics": {"buffered_events": {"mean": 5}}},
                "S7": {"metrics": {"message_loss_pct": {"mean": 0}}}
            }
        }
        self.mock_raw_results = {
            "S1": [{"duration_sec": 1.1}],
            "S2": [{"duration_sec": 1.2}],
            "S3": [{"events": [{"sensor_timestamp": "2026-07-16T09:02:00.000Z", "decision_timestamp": "2026-07-16T09:02:00.120Z"}]}],
            "S4": [{"events": [{"is_state_clamped": True}]}],
            "S5": [{"events": [{"was_buffered": True}]}],
            "S6": [{"events": [{"timestamp": "2026-07-16T09:05:03.400Z"}]}],
            "S7": [{"events": [{"zone_id": "4A"}]}]
        }

    def test_chart_engine_build_all(self):
        engine = ChartEngine(theme="dark")
        charts = engine.build_all(self.mock_metrics, self.mock_raw_results)

        self.assertEqual(len(charts), 10)
        expected_keys = [
            "decision_latency_boxplot",
            "decision_latency_histogram",
            "lateral_propagation_bar",
            "lateral_propagation_ci",
            "false_positive_trend",
            "offline_buffering_timeline",
            "message_integrity_heatmap",
            "cross_scenario_summary",
            "state_transition_timeline",
            "execution_timeline"
        ]
        for key in expected_keys:
            self.assertIn(key, charts)
            spec = charts[key]
            self.assertIn("data", spec)
            self.assertIn("layout", spec)
            self.assertIsInstance(spec["data"], list)
            self.assertGreater(len(spec["data"]), 0)

    def test_chart_engine_empty_input_fallback(self):
        engine = ChartEngine(theme="light")
        charts = engine.build_all({}, {})

        self.assertEqual(len(charts), 10)
        for key, spec in charts.items():
            self.assertIn("data", spec)
            self.assertGreater(len(spec["data"]), 0)


if __name__ == "__main__":
    unittest.main()
