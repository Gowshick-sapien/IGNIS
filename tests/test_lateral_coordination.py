import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import time
import sys
import os

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fog_node_runner import FogNodeRunner

class TestLateralCoordination(unittest.TestCase):
    
    @patch('paho.mqtt.client.Client')
    @patch('src.fog_node_runner.FogNode')
    def setUp(self, mock_fog_node, mock_mqtt_client):
        # Prevent actually loading files by overriding load_config
        self.mock_config = {
            "zone_id": "4C",
            "lateral_warning_timeout_sec": 30,
            "neighbors": [
                { "zone_id": "4B", "bearing_from_neighbor": 180.0, "bearing_tolerance": 45.0, "distance_km": 8.0 }
            ]
        }
        with patch.dict(os.environ, {"ZONE_ID": "4C", "CONFIG_PATH": "mock_path"}):
            with patch.object(FogNodeRunner, 'load_config', return_value=self.mock_config):
                self.runner = FogNodeRunner()
                
    def test_wind_alignment_direct_hit(self):
        # 180 is pointing directly at target 180
        self.assertTrue(self.runner.check_wind_alignment(180.0, 180.0, 45.0))

    def test_wind_alignment_within_tolerance(self):
        # 200 is within 180 ± 45
        self.assertTrue(self.runner.check_wind_alignment(200.0, 180.0, 45.0))
        # 150 is within 180 ± 45
        self.assertTrue(self.runner.check_wind_alignment(150.0, 180.0, 45.0))

    def test_wind_alignment_outside_tolerance(self):
        # 230 is outside 180 ± 45
        self.assertFalse(self.runner.check_wind_alignment(230.0, 180.0, 45.0))
        # 130 is outside 180 ± 45
        self.assertFalse(self.runner.check_wind_alignment(130.0, 180.0, 45.0))

    def test_wind_alignment_wraparound(self):
        # Wind 350, bearing 10, tolerance 30. Diff is 20, should be true
        self.assertTrue(self.runner.check_wind_alignment(350.0, 10.0, 30.0))
        # Wind 10, bearing 350, tolerance 30. Diff is 20, should be true
        self.assertTrue(self.runner.check_wind_alignment(10.0, 350.0, 30.0))

    def test_wind_alignment_wraparound_miss(self):
        # Wind 330, bearing 10, tolerance 30. Diff is 40, should be false
        self.assertFalse(self.runner.check_wind_alignment(330.0, 10.0, 30.0))

    def test_vector_wind_avg_normal(self):
        readings = [
            {"wind_dir_deg": 170.0, "wind_speed_kmh": 10.0},
            {"wind_dir_deg": 190.0, "wind_speed_kmh": 20.0}
        ]
        avg_dir, avg_speed = self.runner.compute_vector_wind_average(readings)
        self.assertAlmostEqual(avg_dir, 180.0, places=1)
        self.assertAlmostEqual(avg_speed, 15.0, places=1)

    def test_vector_wind_avg_wraparound(self):
        readings = [
            {"wind_dir_deg": 350.0, "wind_speed_kmh": 10.0},
            {"wind_dir_deg": 10.0, "wind_speed_kmh": 10.0}
        ]
        avg_dir, avg_speed = self.runner.compute_vector_wind_average(readings)
        self.assertAlmostEqual(avg_dir, 0.0, places=1)
        self.assertAlmostEqual(avg_speed, 10.0, places=1)

    def test_lateral_warning_triggers_preemptive(self):
        payload = {
            "zone_id": "4B",
            "state": "RED",
            "wind_dir_deg": 180.0,
            "wind_speed_kmh": 20.0,
            "timestamp": "2026-07-06T12:00:00Z"
        }
        self.runner._handle_lateral_warning(payload)
        
        # Verify warning registered
        self.assertIn("4B", self.runner.active_lateral_warnings)
        
        # Mock active edge node records
        self.runner.node_states = {
            "4C-E1": {"whi": 0.1, "state": "GREEN", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        }
        
        # Capture self.client_cloud.publish call
        self.runner.client_cloud.publish = MagicMock()
        self.runner.client_local.publish = MagicMock()
        
        # Run state evaluation
        self.runner.evaluate_and_publish_zone_status()
        
        # Verify preemptive state raised to YELLOW
        # Find the publish call for zone_state
        state_payload = None
        for call in self.runner.client_cloud.publish.call_args_list:
            args, kwargs = call
            payload_dict = json.loads(args[1])
            if payload_dict.get("message_type") == "zone_state":
                state_payload = payload_dict
                break
                
        self.assertIsNotNone(state_payload)
        self.assertEqual(state_payload["state"], "YELLOW")
        self.assertTrue(state_payload["preemptive_escalation"])
        self.assertEqual(len(state_payload["lateral_warning_sources"]), 1)
        self.assertEqual(state_payload["lateral_warning_sources"][0]["zone_id"], "4B")

    def test_lateral_warning_structured_object(self):
        payload = {
            "zone_id": "4B",
            "state": "RED",
            "wind_dir_deg": 180.0,
            "wind_speed_kmh": 20.0,
            "timestamp": "2026-07-06T12:00:00Z"
        }
        self.runner._handle_lateral_warning(payload)
        
        warning = self.runner.active_lateral_warnings.get("4B")
        self.assertIsNotNone(warning)
        self.assertEqual(warning["zone_id"], "4B")
        self.assertEqual(warning["state"], "RED")
        self.assertLessEqual(warning["timestamp"], time.time())

    def test_lateral_warning_ignored_wrong_bearing(self):
        # Wind blowing North (0) away from South (4C)
        payload = {
            "zone_id": "4B",
            "state": "RED",
            "wind_dir_deg": 0.0,
            "wind_speed_kmh": 20.0,
            "timestamp": "2026-07-06T12:00:00Z"
        }
        self.runner._handle_lateral_warning(payload)
        self.assertNotIn("4B", self.runner.active_lateral_warnings)

    def test_lateral_warning_expiry(self):
        # Directly insert an old warning
        self.runner.active_lateral_warnings["4B"] = {
            "zone_id": "4B",
            "state": "RED",
            "timestamp": time.time() - 35 # older than 30s timeout
        }
        
        # Mock active edge node records
        self.runner.node_states = {
            "4C-E1": {"whi": 0.1, "state": "GREEN", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        }
        self.runner.client_cloud.publish = MagicMock()
        self.runner.client_local.publish = MagicMock()
        
        self.runner.evaluate_and_publish_zone_status()
        
        # Old warning should be expired, state should remain GREEN
        self.assertNotIn("4B", self.runner.active_lateral_warnings)
        published_payload = json.loads(self.runner.client_cloud.publish.call_args[0][1])
        self.assertEqual(published_payload["state"], "GREEN")
        self.assertFalse(published_payload["preemptive_escalation"])

    def test_own_broadcast_ignored(self):
        # Warning from 4C to 4C should be ignored
        payload = {
            "zone_id": "4C",
            "state": "RED",
            "wind_dir_deg": 180.0,
            "wind_speed_kmh": 20.0,
            "timestamp": "2026-07-06T12:00:00Z"
        }
        self.runner._handle_lateral_warning(payload)
        self.assertNotIn("4C", self.runner.active_lateral_warnings)

    def test_config_merge_defaults(self):
        mock_zones_config = {
            "defaults": {
                "weights": { "temp": 0.2 },
                "lateral_warning_timeout_sec": 30
            },
            "zones": {
                "4C": {
                    "zone_name": "Simlipal South",
                    "neighbors": [{"zone_id": "4B"}]
                }
            }
        }
        
        config_json = json.dumps(mock_zones_config)
        with patch("builtins.open", mock_open(read_data=config_json)):
            with patch("os.path.exists", return_value=True):
                loaded_config = self.runner.load_config("dummy_path")
                
                # Defaults merged
                self.assertEqual(loaded_config["weights"], { "temp": 0.2 })
                self.assertEqual(loaded_config["lateral_warning_timeout_sec"], 30)
                # Overrides merged
                self.assertEqual(loaded_config["zone_name"], "Simlipal South")
                self.assertEqual(loaded_config["zone_id"], "4C")

    def test_lateral_spread_scenario_generation(self):
        from src.scenario import ScenarioGenerator
        steps = ScenarioGenerator.get_lateral_spread_scenario(steps=6)
        self.assertEqual(len(steps), 6)
        
        # Verify steps 0-1 are green with wind pointing south (180)
        self.assertEqual(steps[0]["sensor_data"]["wind_dir_deg"], 180.0)
        self.assertEqual(steps[0]["sensor_data"]["temperature_c"], 28.0)
        
        # Verify steps 2-3 are yellow/orange
        self.assertEqual(steps[2]["sensor_data"]["temperature_c"], 38.0)
        
        # Verify steps 4-5 are red
        self.assertEqual(steps[4]["sensor_data"]["temperature_c"], 48.0)

if __name__ == '__main__':
    unittest.main()
