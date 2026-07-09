import unittest
import sys
import os
import time
from unittest.mock import MagicMock

# Mock paho-mqtt dependencies for host testing
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fog_node_runner import FogNodeRunner


class TestFogNodeAggregation(unittest.TestCase):
    def setUp(self):
        # Sample configuration mimicking config/zone_config.json
        self.config = {
            "zone_id": "4B",
            "weights": {
                "temperature_c": 0.20,
                "humidity_pct": 0.15,
                "wind_speed_kmh": 0.10,
                "soil_moisture_pct": 0.15,
                "gas_ppm": 0.15,
                "thermal_anomaly_c": 0.15,
                "time_of_day": 0.05,
                "seasonal_baseline": 0.05
            },
            "sensor_limits": {
                "temperature_c": {"min": 20.0, "max": 45.0, "confirmation_threshold": 40.0},
                "humidity_pct": {"min": 15.0, "max": 70.0, "confirmation_threshold": 25.0},
                "wind_speed_kmh": {"min": 0.0, "max": 40.0, "confirmation_threshold": 25.0},
                "soil_moisture_pct": {"min": 5.0, "max": 35.0, "confirmation_threshold": 10.0},
                "gas_ppm": {"min": 10.0, "max": 100.0, "confirmation_threshold": 30.0},
                "thermal_anomaly_c": {"min": 0.0, "max": 10.0, "confirmation_threshold": 3.0}
            },
            "state_thresholds": {
                "GREEN": 0.0,
                "YELLOW": 0.35,
                "ORANGE": 0.60,
                "RED": 0.80
            }
        }
        
        # Override FogNodeRunner creation so we don't start MQTT threads during test init
        class MockFogNodeRunner(FogNodeRunner):
            def __init__(self, config):
                self.zone_id = "4B"
                self.config = config
                from src.fog_node import FogNode
                self.fog_processor = FogNode(self.zone_id, self.config)
                self.node_states = {}
                self.last_zone_state = "GREEN"
                # Mock client
                class MockClient:
                    def __init__(self):
                        self.published = []
                    def publish(self, topic, payload):
                        self.published.append((topic, json.loads(payload)))
                self.client = MockClient()

        import json
        self.runner = MockFogNodeRunner(self.config)

    def test_all_green_aggregation(self):
        # Mock green readings for three nodes
        self.runner.node_states["E11"] = {
            "state": "GREEN", "whi": 0.15, "is_state_clamped": False, 
            "confirming_sensors": [], "actions_logged": [],
            "raw_reading": {"node_id": "E11"}
        }
        self.runner.node_states["E12"] = {
            "state": "GREEN", "whi": 0.20, "is_state_clamped": False, 
            "confirming_sensors": [], "actions_logged": [],
            "raw_reading": {"node_id": "E12"}
        }
        self.runner.node_states["E13"] = {
            "state": "GREEN", "whi": 0.18, "is_state_clamped": False, 
            "confirming_sensors": [], "actions_logged": [],
            "raw_reading": {"node_id": "E13"}
        }
        
        self.runner.evaluate_and_publish_zone_status()
        
        # Verify the published state
        self.assertEqual(len(self.runner.client.published), 1)
        topic, payload = self.runner.client.published[0]
        self.assertEqual(topic, "ignis/v1/zone/4B/fog/state")
        self.assertEqual(payload["state"], "GREEN")
        self.assertAlmostEqual(payload["whi"], 0.20)
        self.assertFalse(payload["is_state_clamped"])
        self.assertCountEqual(payload["active_nodes"], ["E11", "E12", "E13"])

    def test_max_state_escalation(self):
        # E11 GREEN, E13 GREEN, E12 RED (worst case)
        self.runner.node_states["E11"] = {
            "state": "GREEN", "whi": 0.15, "is_state_clamped": False, 
            "confirming_sensors": [], "actions_logged": [],
            "raw_reading": {"node_id": "E11"}
        }
        self.runner.node_states["E12"] = {
            "state": "RED", "whi": 0.85, "is_state_clamped": False, 
            "confirming_sensors": ["temperature_c", "gas_ppm", "thermal_anomaly_c"], 
            "actions_logged": ["activate_mist_perimeter", "emergency_alert_control_center"],
            "raw_reading": {"node_id": "E12"}
        }
        self.runner.node_states["E13"] = {
            "state": "GREEN", "whi": 0.18, "is_state_clamped": False, 
            "confirming_sensors": [], "actions_logged": [],
            "raw_reading": {"node_id": "E13"}
        }
        
        self.runner.evaluate_and_publish_zone_status()
        
        # Verify state transition triggered state, alert and action log publications
        # Wait, since last_zone_state defaults to GREEN, transition to RED triggers alert & action_log
        self.assertEqual(len(self.runner.client.published), 3)
        
        state_topic, state_payload = self.runner.client.published[0]
        self.assertEqual(state_topic, "ignis/v1/zone/4B/fog/state")
        self.assertEqual(state_payload["state"], "RED")
        self.assertAlmostEqual(state_payload["whi"], 0.85)
        self.assertCountEqual(state_payload["confirming_sensors"], ["temperature_c", "gas_ppm", "thermal_anomaly_c"])
        
        alert_topic, alert_payload = self.runner.client.published[1]
        self.assertEqual(alert_topic, "ignis/v1/zone/4B/fog/alert")
        self.assertEqual(alert_payload["severity"], "RED")
        self.assertEqual(alert_payload["source_node"], "E12")
        
        action_topic, action_payload = self.runner.client.published[2]
        self.assertEqual(action_topic, "ignis/v1/zone/4B/fog/action_log")
        self.assertCountEqual(action_payload["actions"], ["activate_mist_perimeter", "emergency_alert_control_center"])

    def test_clamp_propagation(self):
        # E12 has elevated WHI but clamped to YELLOW (1 confirmation)
        self.runner.node_states["E12"] = {
            "state": "YELLOW", "whi": 0.65, "is_state_clamped": True, 
            "confirming_sensors": ["gas_ppm"], "actions_logged": [],
            "raw_reading": {"node_id": "E12"}
        }
        
        self.runner.evaluate_and_publish_zone_status()
        
        # Aggregated zone should be YELLOW and clamped
        topic, payload = self.runner.client.published[0]
        self.assertEqual(payload["state"], "YELLOW")
        self.assertTrue(payload["is_state_clamped"])
        self.assertCountEqual(payload["confirming_sensors"], ["gas_ppm"])

if __name__ == '__main__':
    unittest.main()
