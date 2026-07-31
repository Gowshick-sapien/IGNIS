"""
Unit tests for Event Stream Metric Derivation (Phase G1 Fix)
"""

import unittest
from src.metrics_collector import (
    compute_fog_decision_latency,
    compute_lateral_propagation,
    derive_metric,
    calculate_decision_latency,
    calculate_lateral_propagation,
    DIRECT_METRICS,
    DERIVED_METRICS,
    ASSERTION_METRICS
)


class TestMetricDerivation(unittest.TestCase):

    def test_metric_classification_sets(self):
        self.assertIn("false_positive_count", DIRECT_METRICS)
        self.assertIn("offline_continuity", DIRECT_METRICS)
        self.assertIn("fog_decision_latency", DERIVED_METRICS)
        self.assertIn("lateral_propagation_time", DERIVED_METRICS)
        self.assertIn("max_state", ASSERTION_METRICS)

    # 1. Fog Decision Latency Tests
    def test_fog_decision_latency_valid_sequence(self):
        events = [
            {"message_type": "alert", "timestamp": "2026-07-24T10:00:00Z", "_topic": "ignis/v1/fog/zone/4B/alert"},
            {"message_type": "zone_state", "timestamp": "2026-07-24T10:00:12Z", "state": "ORANGE", "_topic": "ignis/v1/fog/zone/4B/state"}
        ]
        lat = derive_metric(events, "fog_decision_latency")
        self.assertIsNotNone(lat)
        self.assertEqual(lat, 12.0)

    def test_fog_decision_latency_missing_alert(self):
        events = [
            {"message_type": "zone_state", "timestamp": "2026-07-24T10:00:12Z", "state": "RED"}
        ]
        lat = derive_metric(events, "fog_decision_latency")
        self.assertIsNone(lat)

    def test_fog_decision_latency_missing_decision(self):
        events = [
            {"message_type": "alert", "timestamp": "2026-07-24T10:00:00Z"}
        ]
        lat = derive_metric(events, "fog_decision_latency")
        self.assertIsNone(lat)

    def test_fog_decision_latency_multiple_alerts_decisions(self):
        events = [
            {"message_type": "alert", "timestamp": "2026-07-24T10:00:00Z"},
            {"message_type": "alert", "timestamp": "2026-07-24T10:00:02Z"},
            {"message_type": "zone_state", "timestamp": "2026-07-24T10:00:05Z", "state": "YELLOW"},
            {"message_type": "zone_state", "timestamp": "2026-07-24T10:00:10Z", "state": "RED"}
        ]
        lat = derive_metric(events, "fog_decision_latency")
        self.assertEqual(lat, 5.0)

    # 2. Lateral Propagation Tests
    def test_lateral_propagation_valid_sequence(self):
        events = [
            {"_topic": "ignis/v1/fog/zone/4B/state", "zone_id": "4B", "state": "RED", "timestamp": "2026-07-24T10:00:00Z"},
            {"_topic": "ignis/v1/fog/zone/4C/state", "zone_id": "4C", "state": "YELLOW", "timestamp": "2026-07-24T10:00:03Z"}
        ]
        prop = derive_metric(events, "lateral_propagation_time")
        self.assertIsNotNone(prop)
        self.assertEqual(prop, 3.0)

    def test_lateral_propagation_missing_source(self):
        events = [
            {"_topic": "ignis/v1/fog/zone/4C/state", "zone_id": "4C", "state": "YELLOW", "timestamp": "2026-07-24T10:00:03Z"}
        ]
        prop = derive_metric(events, "lateral_propagation_time")
        self.assertIsNone(prop)

    def test_lateral_propagation_missing_destination(self):
        events = [
            {"_topic": "ignis/v1/fog/zone/4B/state", "zone_id": "4B", "state": "GREEN", "timestamp": "2026-07-24T10:00:00Z"}
        ]
        prop = derive_metric(events, "lateral_propagation_time")
        self.assertIsNone(prop)

    # 3. Statistical Aggregation Pipeline Verification
    def test_derived_metric_statistical_aggregation(self):
        mock_results = [
            {"events": [
                {"message_type": "alert", "timestamp": "2026-07-24T10:00:00Z"},
                {"message_type": "zone_state", "timestamp": "2026-07-24T10:00:10Z", "state": "RED"}
            ]},
            {"events": [
                {"message_type": "alert", "timestamp": "2026-07-24T10:01:00Z"},
                {"message_type": "zone_state", "timestamp": "2026-07-24T10:01:14Z", "state": "RED"}
            ]}
        ]

        stats = calculate_decision_latency(mock_results)
        self.assertEqual(stats["sample_count"], 2)
        self.assertEqual(stats["mean"], 12.0)
        self.assertEqual(stats["median"], 12.0)
        self.assertIn("confidence95", stats)
        self.assertEqual(len(stats["confidence95"]), 2)


if __name__ == "__main__":
    unittest.main()
