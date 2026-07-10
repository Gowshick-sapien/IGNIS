import unittest
import sys
import os
import json
import time
import calendar
from unittest.mock import MagicMock, patch

# Mock MQTT, InfluxDB, and dotenv libraries for host-side unit testing
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
sys.modules['influxdb_client'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fog_node_runner import FogNodeRunner
from src.cloud_ingestor.mqtt_service import CloudMQTTService

class TestCloudResilience(unittest.TestCase):
    def setUp(self):
        # Configuration mock
        self.config = {
            "zone_id": "4B",
            "weights": {
                "temperature_c": 0.2, "humidity_pct": 0.15, "wind_speed_kmh": 0.1,
                "soil_moisture_pct": 0.15, "gas_ppm": 0.15, "thermal_anomaly_c": 0.15,
                "time_of_day": 0.05, "seasonal_baseline": 0.05
            },
            "sensor_limits": {
                "temperature_c": {"min": 20.0, "max": 45.0, "confirmation_threshold": 40.0},
                "humidity_pct": {"min": 15.0, "max": 70.0, "confirmation_threshold": 25.0},
                "wind_speed_kmh": {"min": 0.0, "max": 40.0, "confirmation_threshold": 25.0},
                "soil_moisture_pct": {"min": 5.0, "max": 35.0, "confirmation_threshold": 10.0},
                "gas_ppm": {"min": 10.0, "max": 100.0, "confirmation_threshold": 30.0},
                "thermal_anomaly_c": {"min": 0.0, "max": 10.0, "confirmation_threshold": 3.0}
            },
            "state_thresholds": {"GREEN": 0.0, "YELLOW": 0.35, "ORANGE": 0.6, "RED": 0.8}
        }
        
        # Mock FogNodeRunner with no actual sockets
        class MockFogNodeRunner(FogNodeRunner):
            def __init__(self, config):
                self.zone_id = "4B"
                self.config = config
                from src.fog_node import FogNode
                self.fog_processor = FogNode(self.zone_id, self.config)
                self.node_states = {}
                self.last_zone_state = "GREEN"
                self.override_active = False
                self.override_state = "NONE"
                self.processed_command_ids = set()
                self.last_sequence_number = -1
                
                # Mock local and cloud publish lists
                class MockClient:
                    def __init__(self):
                        self.published = []
                    def publish(self, topic, payload, retain=False):
                        self.published.append((topic, json.loads(payload)))
                self.client_local = MockClient()
                self.client_cloud = MockClient()

        self.runner = MockFogNodeRunner(self.config)

    def test_advisory_command_valid(self):
        # A valid state override to RED
        cmd_id = "cmd-12345"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "command_id": cmd_id,
            "sequence_number": 1,
            "zone_id": "4B",
            "issued_by": "operator_alpha",
            "timestamp": timestamp,
            "ttl": 300,
            "command": "set_override_state",
            "parameters": {"state": "RED"}
        }
        
        msg = MagicMock()
        msg.topic = "ignis/v1/advisory/zone/4B/command"
        msg.payload = json.dumps(payload).encode()
        
        self.runner.on_message_cloud(None, None, msg)
        
        # Verify success response and state override clamping to RED
        self.assertTrue(self.runner.override_active)
        self.assertEqual(self.runner.override_state, "RED")
        
        # Check that response message was published
        response_published = [p for p in self.runner.client_cloud.published if "response" in p[0]]
        self.assertEqual(len(response_published), 1)
        topic, body = response_published[0]
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["command_id"], cmd_id)

    def test_advisory_command_duplicate_rejected(self):
        # Insert cmd_id to simulation cache
        cmd_id = "cmd-dup-999"
        self.runner.processed_command_ids.add(cmd_id)
        
        payload = {
            "command_id": cmd_id,
            "sequence_number": 2,
            "zone_id": "4B",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ttl": 300,
            "command": "set_override_state",
            "parameters": {"state": "RED"}
        }
        msg = MagicMock()
        msg.payload = json.dumps(payload).encode()
        
        self.runner.on_message_cloud(None, None, msg)
        
        # State override must NOT be active
        self.assertFalse(self.runner.override_active)
        
        # Check FAILED response was published
        response_published = [p for p in self.runner.client_cloud.published if "response" in p[0]]
        self.assertEqual(len(response_published), 1)
        self.assertEqual(response_published[0][1]["status"], "FAILED")
        self.assertIn("Duplicate", response_published[0][1]["error_reason"])

    def test_advisory_command_expired_rejected(self):
        # Command older than TTL (timestamp set to 1 hour ago)
        cmd_id = "cmd-expired-777"
        expired_ts = calendar.timegm(time.gmtime()) - 3600 # 1 hour ago
        payload = {
            "command_id": cmd_id,
            "sequence_number": 3,
            "zone_id": "4B",
            "timestamp": str(expired_ts),
            "ttl": 300, # 5 min TTL
            "command": "set_override_state",
            "parameters": {"state": "RED"}
        }
        msg = MagicMock()
        msg.payload = json.dumps(payload).encode()
        
        self.runner.on_message_cloud(None, None, msg)
        
        self.assertFalse(self.runner.override_active)
        response_published = [p for p in self.runner.client_cloud.published if "response" in p[0]]
        self.assertEqual(len(response_published), 1)
        self.assertEqual(response_published[0][1]["status"], "FAILED")
        self.assertIn("expired", response_published[0][1]["error_reason"])

    def test_ingestor_offline_buffering_and_flush(self):
        # Mock database connection wrapper
        db_mock = MagicMock()
        db_mock.ping.return_value = False # DB offline
        
        service = CloudMQTTService(db_mock)
        
        # Process a telemetry reading message while DB offline
        payload = {
            "node_id": "E11",
            "zone_id": "4B",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sequence": 1,
            "temperature_c": 35.0, "humidity_pct": 20.0, "wind_speed_kmh": 10.0,
            "wind_dir_deg": 180.0, "soil_moisture_pct": 12.0, "gas_ppm": 15.0,
            "thermal_anomaly_c": 0.0, "light_lux": 40000.0, "rain_mm": 0.0
        }
        
        # Try writing telemetry
        service.process_telemetry(payload, "4B", "E11", calendar.timegm(time.gmtime()))
        
        # Verify it was added to offline buffer (both telemetry and performance metrics)
        self.assertEqual(len(service.offline_buffer), 2)
        self.assertEqual(service.offline_buffer[0][0], "telemetry")
        self.assertEqual(service.offline_buffer[1][0], "performance_metrics")
        
        # Restore DB connection (ping returns True) and flush buffer
        db_mock.ping.return_value = True
        service.flush_buffer()
        
        # Buffer must be empty and write record called 2 times
        self.assertEqual(len(service.offline_buffer), 0)
        self.assertEqual(db_mock.write_record.call_count, 2)

if __name__ == '__main__':
    unittest.main()
