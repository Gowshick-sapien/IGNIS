import os
import sys
import unittest
import math

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metrics_collector import (
    calculate_stats,
    calculate_decision_latency,
    calculate_lateral_propagation,
    calculate_false_positive_rate,
    calculate_offline_continuity,
    calculate_concurrent_zone_integrity,
    compute_metrics
)

class TestMetricsCollector(unittest.TestCase):
    
    def test_calculate_decision_latency_valid(self):
        # S3 scenario results mock
        results = [
            {
                "events": [
                    {
                        "_topic": "ignis/v1/fog/zone/4B/state",
                        "sensor_timestamp": "2026-07-16T09:00:00.000Z",
                        "decision_timestamp": "2026-07-16T09:00:00.150Z"
                    },
                    {
                        "message_type": "zone_state",
                        "sensor_timestamp": "2026-07-16T09:00:04.000Z",
                        "decision_timestamp": "2026-07-16T09:00:04.080Z"
                    }
                ]
            }
        ]
        
        metrics = calculate_decision_latency(results)
        self.assertEqual(metrics["sample_count"], 2)
        self.assertAlmostEqual(metrics["min"], 0.08)
        self.assertAlmostEqual(metrics["max"], 0.15)
        self.assertAlmostEqual(metrics["mean"], 0.115)
        self.assertAlmostEqual(metrics["median"], 0.115)
        self.assertEqual(len(metrics["confidence95"]), 2)

    def test_calculate_decision_latency_empty(self):
        metrics = calculate_decision_latency([])
        self.assertEqual(metrics["status"], "INVALID")
        self.assertIn("No matching events", metrics["reason"])

    def test_calculate_lateral_propagation_valid(self):
        # S6 scenario results mock
        results = [
            {
                "events": [
                    {
                        "_topic": "ignis/v1/fog/zone/4B/state",
                        "state": "RED",
                        "timestamp": "2026-07-16T09:00:00.000Z"
                    },
                    {
                        "_topic": "ignis/v1/fog/zone/4C/state",
                        "state": "YELLOW",
                        "timestamp": "2026-07-16T09:00:03.400Z"
                    }
                ]
            }
        ]
        
        metrics = calculate_lateral_propagation(results)
        self.assertEqual(metrics["sample_count"], 1)
        self.assertAlmostEqual(metrics["mean"], 3.4)
        self.assertAlmostEqual(metrics["min"], 3.4)
        self.assertAlmostEqual(metrics["max"], 3.4)
        self.assertAlmostEqual(metrics["median"], 3.4)

    def test_calculate_lateral_propagation_empty(self):
        metrics = calculate_lateral_propagation([])
        self.assertEqual(metrics["status"], "INVALID")
        self.assertIn("No matching events", metrics["reason"])

    def test_calculate_false_positive_rate_valid(self):
        # S4 scenario results mock
        results = [
            {
                "events": [
                    {"_topic": "ignis/v1/fog/zone/4B/state", "state": "YELLOW", "is_state_clamped": True}
                ]
            },
            {
                "events": [
                    {"_topic": "ignis/v1/fog/zone/4B/state", "state": "RED", "is_state_clamped": False}
                ]
            }
        ]
        metrics = calculate_false_positive_rate(results)
        self.assertEqual(metrics["total_trials"], 2)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertAlmostEqual(metrics["rate"], 0.5)
        self.assertAlmostEqual(metrics["is_clamped_ratio"], 0.5)

    def test_calculate_offline_continuity_valid(self):
        # S5 scenario results mock
        results = [
            {
                "logs": ["[Offline Continuity] Action taken"],
                "events": [
                    {"was_buffered": True, "buffer_flush_timestamp": "2026-07-16T09:00:00.000Z"}
                ]
            }
        ]
        metrics = calculate_offline_continuity(results)
        self.assertTrue(metrics["uninterrupted_execution"])
        self.assertEqual(metrics["total_enqueued"], 1)
        self.assertEqual(metrics["flushed_count"], 1)
        self.assertAlmostEqual(metrics["flush_success_rate"], 1.0)

    def test_calculate_concurrent_zone_integrity_valid(self):
        # S7 scenario results mock
        results = [
            {
                "events": [
                    {"_topic": "ignis/v1/fog/zone/4A/state", "zone_id": "4A"},
                    {"_topic": "ignis/v1/fog/zone/4A/state", "zone_id": "4B"} # cross-talk
                ]
            }
        ]
        metrics = calculate_concurrent_zone_integrity(results)
        self.assertEqual(metrics["cross_talk_detected"], 1)
        self.assertEqual(metrics["total_messages_processed"], 2)

    def test_compute_metrics_all_scenarios(self):
        raw_results = {
            "S1": [{"events": [{"_topic": "ignis/v1/fog/zone/4B/state", "state": "GREEN"}]}],
            "S2": [{"events": [{"_topic": "ignis/v1/fog/zone/4B/state", "state": "YELLOW"}]}],
            "S3": [
                {
                    "events": [
                        {
                            "_topic": "ignis/v1/fog/zone/4B/state",
                            "state": "RED",
                            "sensor_timestamp": "2026-07-16T09:00:00.000Z",
                            "decision_timestamp": "2026-07-16T09:00:00.120Z"
                        }
                    ]
                }
            ],
            "S4": [
                {
                    "events": [
                        {
                            "_topic": "ignis/v1/fog/zone/4B/state",
                            "state": "YELLOW",
                            "is_state_clamped": True
                        }
                    ]
                }
            ],
            "S5": [
                {
                    "logs": ["[Offline Continuity] Action taken"],
                    "events": [
                        {
                            "was_buffered": True,
                            "buffer_flush_timestamp": "2026-07-16T09:00:00.000Z"
                        }
                    ]
                }
            ],
            "S6": [
                {
                    "events": [
                        {
                            "_topic": "ignis/v1/fog/zone/4B/state",
                            "state": "RED",
                            "timestamp": "2026-07-16T09:00:00.000Z"
                        },
                        {
                            "_topic": "ignis/v1/fog/zone/4C/state",
                            "state": "YELLOW",
                            "timestamp": "2026-07-16T09:00:03.400Z"
                        }
                    ]
                }
            ],
            "S7": [
                {
                    "events": [
                        {
                            "_topic": "ignis/v1/fog/zone/4A/state",
                            "zone_id": "4A"
                        }
                    ]
                }
            ]
        }
        
        output = compute_metrics(raw_results)
        self.assertIn("experiment_metadata", output)
        self.assertIn("scenario_results", output)
        self.assertIn("summary", output)
        
        # Check specific scenario statuses
        s3_res = output["scenario_results"]["S3"]
        self.assertEqual(s3_res["status"], "PASS")
        self.assertEqual(s3_res["trials"], 1)

    def test_calculate_stats_zero_variance(self):
        data = [0.0, 0.0, 0.0, 0.0, 0.0]
        stats = calculate_stats(data)
        self.assertEqual(stats["mean"], 0.0)
        self.assertEqual(stats["std_dev"], 0.0)
        self.assertEqual(stats["confidence95"], [0.0, 0.0])
        self.assertFalse(any(math.isnan(x) for x in stats["confidence95"]))

if __name__ == "__main__":
    unittest.main()
