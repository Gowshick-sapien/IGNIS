import unittest
import json
import time
from unittest.mock import MagicMock, patch, mock_open

# Ensure paho and other dependencies are mocked if run without them
import sys
import os
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
sys.modules['influxdb_client'] = MagicMock()

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.clock import Clock, MockClock, default_clock
from src.events import DecisionEvent, AlertEvent, ActionEvent, CloudReportEvent, ScenarioEvent
from src.buffered_publisher import BufferedPublisher
from src.control_center.scenario_service import ScenarioService
from src.fog_node_runner import FogNodeRunner
import src.cloud_dashboard.database
import src.cloud_dashboard.app

class TestClockMockability(unittest.TestCase):
    def test_clock_production(self):
        clock = Clock()
        t1 = clock.time()
        time.sleep(0.01)
        t2 = clock.time()
        self.assertGreater(t2, t1)
        
        # Test strftime output format
        ts_str = clock.strftime("%Y-%m-%dT%H:%M:%SZ", t1)
        self.assertTrue(ts_str.endswith("Z"))

    def test_mock_clock_deterministic(self):
        clock = MockClock(start_time=1000.0)
        self.assertEqual(clock.time(), 1000.0)
        
        clock.advance(10.5)
        self.assertEqual(clock.time(), 1010.5)
        
        clock.sleep(5.0)
        self.assertEqual(clock.time(), 1015.5)
        self.assertEqual(clock.sleeps, [5.0])
        
        # Test strftime
        ts_str = clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        # 1015.5 in GMT: 1970-01-01T00:16:55Z
        self.assertEqual(ts_str, "1970-01-01T00:16:55Z")

class TestEventSerialization(unittest.TestCase):
    def test_decision_event(self):
        event = DecisionEvent(
            scenario="S3",
            zone_id="4B",
            node_id="4B-E2",
            sensor_timestamp="2026-07-14T22:00:00Z",
            decision_timestamp="2026-07-14T22:00:01Z",
            previous_state="GREEN",
            new_state="YELLOW",
            whi=0.45,
            confirmation_count=2,
            is_clamped=False
        )
        d = event.to_dict()
        self.assertEqual(d["scenario"], "S3")
        self.assertEqual(d["whi"], 0.45)
        
        event2 = DecisionEvent.from_dict(d)
        self.assertEqual(event, event2)

    def test_alert_event(self):
        event = AlertEvent(
            scenario="S3",
            zone_id="4B",
            timestamp="2026-07-14T22:00:00Z",
            severity="WARNING",
            source_node="4B-E2",
            whi=0.55
        )
        d = event.to_dict()
        event2 = AlertEvent.from_dict(d)
        self.assertEqual(event, event2)

    def test_action_event(self):
        event = ActionEvent(
            scenario="S3",
            zone_id="4B",
            timestamp="2026-07-14T22:00:00Z",
            actions=["ACTIVATE_SPRINKLERS", "SOUND_ALARM"],
            reason="High fire risk"
        )
        d = event.to_dict()
        event2 = ActionEvent.from_dict(d)
        self.assertEqual(event, event2)

    def test_cloud_report_event(self):
        event = CloudReportEvent(
            scenario="S3",
            zone_id="4B",
            node_id="4B-E2",
            timestamp="2026-07-14T22:00:00Z",
            was_buffered=True,
            buffer_flush_timestamp="2026-07-14T22:05:00Z"
        )
        d = event.to_dict()
        event2 = CloudReportEvent.from_dict(d)
        self.assertEqual(event, event2)

    def test_scenario_event(self):
        event = ScenarioEvent(
            scenario="S3",
            event_type="start",
            timestamp="2026-07-14T22:00:00Z",
            step_index=0,
            total_steps=5
        )
        d = event.to_dict()
        event2 = ScenarioEvent.from_dict(d)
        self.assertEqual(event, event2)

class TestBufferedPublisher(unittest.TestCase):
    def test_buffered_publisher_queuing(self):
        mock_client = MagicMock()
        pub = BufferedPublisher(mock_client, maxlen=5)
        
        # Initially not connected
        self.assertFalse(pub.is_connected)
        
        # Publish should enqueue and return False (since it is not sent directly)
        res = pub.publish("topic1", "payload1")
        self.assertFalse(res)
        self.assertEqual(pub.buffer_size, 1)
        self.assertEqual(list(pub.buffer), [("topic1", "payload1")])
        mock_client.publish.assert_not_called()

    def test_buffered_publisher_flush(self):
        mock_client = MagicMock()
        # Mock client publish returns an object with rc=0 (success)
        mock_res = MagicMock()
        mock_res.rc = 0
        mock_client.publish.return_value = mock_res
        
        pub = BufferedPublisher(mock_client, maxlen=5)
        pub.publish("topic1", "payload1")
        pub.publish("topic2", "payload2")
        self.assertEqual(pub.buffer_size, 2)
        
        # Reconnect
        pub.on_connect()
        self.assertTrue(pub.is_connected)
        
        # Flush
        flushed = pub.flush()
        self.assertEqual(flushed, 2)
        self.assertEqual(pub.buffer_size, 0)
        self.assertEqual(mock_client.publish.call_count, 2)
        mock_client.publish.assert_any_call("topic1", "payload1")
        mock_client.publish.assert_any_call("topic2", "payload2")

    def test_buffered_publisher_overflow(self):
        mock_client = MagicMock()
        pub = BufferedPublisher(mock_client, maxlen=3)
        
        pub.publish("t1", "p1")
        pub.publish("t2", "p2")
        pub.publish("t3", "p3")
        pub.publish("t4", "p4") # Exceeds maxlen=3
        
        self.assertEqual(pub.buffer_size, 3)
        # Oldest "t1", "p1" should be evicted
        self.assertEqual(list(pub.buffer), [("t2", "p2"), ("t3", "p3"), ("t4", "p4")])

    def test_buffered_publisher_publish_success(self):
        mock_client = MagicMock()
        mock_res = MagicMock()
        mock_res.rc = 0
        mock_client.publish.return_value = mock_res
        
        pub = BufferedPublisher(mock_client, maxlen=5)
        pub.on_connect()
        
        res = pub.publish("topic1", "payload1")
        self.assertTrue(res)
        self.assertEqual(pub.buffer_size, 0)
        mock_client.publish.assert_called_once_with("topic1", "payload1")

    def test_buffered_publisher_publish_failure_queuing(self):
        mock_client = MagicMock()
        # Publish fails with rc != 0
        mock_res = MagicMock()
        mock_res.rc = 1 # failure
        mock_client.publish.return_value = mock_res
        
        pub = BufferedPublisher(mock_client, maxlen=5)
        pub.on_connect()
        
        res = pub.publish("topic1", "payload1")
        self.assertFalse(res)
        self.assertEqual(pub.buffer_size, 1)
        self.assertEqual(list(pub.buffer), [("topic1", "payload1")])

class TestScenarioServiceNodeResolution(unittest.TestCase):
    @patch('time.sleep') # prevent test from waiting 4 seconds
    def test_localized_scenario_node_resolution(self, mock_sleep):
        service = ScenarioService(zone_id="4B")
        service.client = MagicMock()
        
        # Override active_nodes to test zone-prefixed IDs
        service.active_nodes = ["4B-E1", "4B-E2", "4B-E3"]
        
        steps = [
            {"sensor_data": {"temp": 25.0}, "seasonal_baseline": 0.5}
        ]
        
        # Run localized scenario (this would normally target E12, now 4B-E2)
        service._run_localized_scenario("S3", steps)
        
        # Check topic publications
        # Expected baseline reset/enforcement on baseline nodes 4B-E1 and 4B-E3:
        # ignis/v1/system/zone/4B/edge/4B-E1/control
        # ignis/v1/system/zone/4B/edge/4B-E3/control
        # And step target publication on target node 4B-E2:
        # ignis/v1/system/zone/4B/edge/4B-E2/control
        
        published_calls = service.client.publish.call_args_list
        published_topics = [call[0][0] for call in published_calls]
        
        # Check for initial baseline enforcement on baseline nodes
        self.assertIn("ignis/v1/system/zone/4B/edge/4B-E1/control", published_topics)
        self.assertIn("ignis/v1/system/zone/4B/edge/4B-E3/control", published_topics)
        
        # Check for scenario step publication on target node 4B-E2
        self.assertIn("ignis/v1/system/zone/4B/edge/4B-E2/control", published_topics)
        
        # Verify no hardcoded "E11", "E12", "E13" topic calls were made
        for topic in published_topics:
            self.assertNotIn("edge/E11/", topic)
            self.assertNotIn("edge/E12/", topic)
            self.assertNotIn("edge/E13/", topic)

class TestFogNodeRunnerResilience(unittest.TestCase):
    @patch('src.fog_node_runner.FogNodeRunner.load_config')
    def setUp(self, mock_load):
        self.config = {
            "zone_id": "4B",
            "neighbors": [],
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
        mock_load.return_value = self.config
        self.clock = MockClock(start_time=1700000000.0)
        self.runner = FogNodeRunner(clock=self.clock)
        self.runner.client_cloud = MagicMock()
        # Re-initialize publisher with mock client
        self.runner.cloud_publisher = BufferedPublisher(self.runner.client_cloud, clock=self.clock)
        self.runner.client_local = MagicMock()

    @patch('src.fog_node_runner.FogNodeRunner.load_config')
    def test_fog_runner_offline_queuing(self, mock_load):
        mock_load.return_value = self.config
        # Ensure offline
        self.assertFalse(self.runner.cloud_publisher.is_connected)
        
        payload = {
            "node_id": "4B-E2",
            "zone_id": "4B",
            "timestamp": "2026-07-14T22:00:00Z",
            "sequence": 1,
            "temperature_c": 35.0, "humidity_pct": 20.0, "wind_speed_kmh": 10.0,
            "wind_dir_deg": 180.0, "soil_moisture_pct": 12.0, "gas_ppm": 15.0,
            "thermal_anomaly_c": 0.0, "light_lux": 40000.0, "rain_mm": 0.0
        }
        
        msg = MagicMock()
        msg.payload = json.dumps(payload).encode()
        self.runner.on_message_local(None, None, msg)
        
        # Telemetry, state heartbeat, transition alert, and lateral broadcast should be enqueued
        self.assertEqual(self.runner.cloud_publisher.buffer_size, 4)
        # Mock client should not have been called to publish
        self.runner.client_cloud.publish.assert_not_called()

    @patch('src.fog_node_runner.FogNodeRunner.load_config')
    def test_fog_runner_reconnect_flush(self, mock_load):
        mock_load.return_value = self.config
        
        # Load and enqueue messages
        payload = {
            "node_id": "4B-E2",
            "zone_id": "4B",
            "timestamp": "2026-07-14T22:00:00Z",
            "sequence": 1,
            "temperature_c": 35.0, "humidity_pct": 20.0, "wind_speed_kmh": 10.0,
            "wind_dir_deg": 180.0, "soil_moisture_pct": 12.0, "gas_ppm": 15.0,
            "thermal_anomaly_c": 0.0, "light_lux": 40000.0, "rain_mm": 0.0
        }
        msg = MagicMock()
        msg.payload = json.dumps(payload).encode()
        self.runner.on_message_local(None, None, msg)
        self.assertEqual(self.runner.cloud_publisher.buffer_size, 4)
        
        # Mock connection success (rc=0)
        mock_res = MagicMock()
        mock_res.rc = 0
        self.runner.client_cloud.publish.return_value = mock_res
        
        self.runner.on_connect_cloud(self.runner.client_cloud, None, None, 0)
        
        # Buffer should be flushed
        self.assertEqual(self.runner.cloud_publisher.buffer_size, 0)
        # client_cloud should have published the messages
        self.assertGreaterEqual(self.runner.client_cloud.publish.call_count, 2)

    @patch('src.fog_node_runner.FogNodeRunner.load_config')
    def test_fog_runner_offline_continuity_logging(self, mock_load):
        mock_load.return_value = self.config
        
        # Send reading that escalates to RED
        payload = {
            "node_id": "4B-E2",
            "zone_id": "4B",
            "timestamp": "2026-07-14T22:00:00Z",
            "sequence": 1,
            "temperature_c": 45.0,        # max temp
            "humidity_pct": 15.0,         # min hum
            "wind_speed_kmh": 40.0,       # max wind
            "wind_dir_deg": 180.0,
            "soil_moisture_pct": 5.0,     # min soil
            "gas_ppm": 100.0,             # max gas
            "thermal_anomaly_c": 10.0,    # max anomaly
            "light_lux": 40000.0,
            "rain_mm": 0.0
        }
        
        msg = MagicMock()
        msg.payload = json.dumps(payload).encode()
        
        # Capture stdout/logger logs
        with self.assertLogs('fog_node_runner', level='INFO') as log:
            self.runner.on_message_local(None, None, msg)
            
            # Check for the expected continuity log message
            continuity_logged = False
            for output in log.output:
                if "[Offline Continuity] Action Log:" in output:
                    continuity_logged = True
                    break
            self.assertTrue(continuity_logged, "Should have logged action log locally while offline")

class TestYAMLScenarioLibrary(unittest.TestCase):
    def test_registry_resolution(self):
        from src.scenarios.scenario_registry import SCENARIO_REGISTRY
        from src.scenarios.base_scenario import BaseScenario
        for sid in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
            self.assertIn(sid, SCENARIO_REGISTRY)
            self.assertTrue(issubclass(SCENARIO_REGISTRY[sid], BaseScenario))

    def test_yaml_schema_conformance(self):
        import glob
        import yaml
        yaml_files = glob.glob("scenarios/s*.yaml")
        self.assertGreaterEqual(len(yaml_files), 7)
        for yf in yaml_files:
            with open(yf, 'r') as f:
                data = yaml.safe_load(f)
                self.assertIn("scenario_id", data)
                self.assertIn("target", data)
                self.assertIn("steps", data)
                self.assertIn("expected_outcome", data)

    @patch('src.scenarios.base_scenario.GenericScenario._reset_all_nodes')
    def test_scenario_runner_execution(self, mock_reset):
        from src.scenarios.scenario_runner import ScenarioRunner
        clock = MockClock()
        runner = ScenarioRunner(clock=clock)
        runner.client = MagicMock()
        runner.client.connect = MagicMock()
        runner.client.publish = MagicMock()
        
        def simulate_events(*args, **kwargs):
            runner.collected_events.append({
                "message_type": "zone_state",
                "state": "YELLOW",
                "is_state_clamped": True,
                "_topic": "ignis/v1/fog/zone/4B/state"
            })
            
        runner.client.publish.side_effect = simulate_events
        results = runner.run_scenario("S4", trials=1)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.scenario, "S4")
        self.assertTrue(res.passed)
        self.assertEqual(res.trial_index, 0)
        self.assertGreater(len(res.events), 0)

class TestChaosController(unittest.TestCase):
    @patch('src.chaos_controller.routes.adapter')
    def test_routes_endpoints(self, mock_adapter):
        from fastapi.testclient import TestClient
        from src.chaos_controller.app import app
        client = TestClient(app)
        
        # 1. Test GET status
        res = client.get("/api/chaos/status")
        self.assertEqual(res.status_code, 200)
        status_data = res.json()
        self.assertIn("disconnected_zones", status_data)
        self.assertIn("killed_containers", status_data)
        
        # 2. Test POST disconnect_cloud
        mock_adapter.disconnect.return_value = {"success": True, "details": "Disconnected", "timestamp": "now"}
        res = client.post("/api/chaos/disconnect_cloud", json={"zone_id": "4B", "duration_sec": 0})
        self.assertEqual(res.status_code, 200)
        mock_adapter.disconnect.assert_called_with("ignis-fog-node-4b", "cloud-net")
        
        # 3. Test POST restore_cloud
        mock_adapter.reconnect.return_value = {"success": True, "details": "Reconnected", "timestamp": "now"}
        res = client.post("/api/chaos/restore_cloud", json={"zone_id": "4B"})
        self.assertEqual(res.status_code, 200)
        mock_adapter.reconnect.assert_called_with("ignis-fog-node-4b", "cloud-net")

        # 4. Test POST kill_container
        mock_adapter.kill.return_value = {"success": True, "details": "Stopped", "timestamp": "now"}
        res = client.post("/api/chaos/kill_container", json={"container_name": "ignis-fog-node-4b", "duration_sec": 0})
        self.assertEqual(res.status_code, 200)
        mock_adapter.kill.assert_called_with("ignis-fog-node-4b")

        # 5. Test POST restart_container
        mock_adapter.restart.return_value = {"success": True, "details": "Restarted", "timestamp": "now"}
        res = client.post("/api/chaos/restart_container", json={"container_name": "ignis-fog-node-4b"})
        self.assertEqual(res.status_code, 200)
        mock_adapter.restart.assert_called_with("ignis-fog-node-4b")

    def test_docker_adapter_methods(self):
        from src.chaos_controller.docker_adapter import DockerAdapter
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_network = MagicMock()
        mock_network.name = "ignis_cloud-net"
        
        mock_client.containers.get.return_value = mock_container
        mock_client.networks.list.return_value = [mock_network]
        
        adapter = DockerAdapter(docker_client=mock_client)
        
        # Test disconnect
        res = adapter.disconnect("ignis-fog-node-4b", "cloud-net")
        self.assertTrue(res["success"])
        mock_network.disconnect.assert_called_with(mock_container)
        
        # Test reconnect
        res = adapter.reconnect("ignis-fog-node-4b", "cloud-net")
        self.assertTrue(res["success"])
        mock_network.connect.assert_called_with(mock_container)
        
        # Test kill
        res = adapter.kill("ignis-fog-node-4b")
        self.assertTrue(res["success"])
        mock_container.stop.assert_called_once()
        
        # Test restart
        res = adapter.restart("ignis-fog-node-4b")
        self.assertTrue(res["success"])
        mock_container.restart.assert_called_once()
        
        # Test get_status
        mock_container.status = "running"
        res = adapter.get_status("ignis-fog-node-4b")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "running")

class TestScenarioFaultInjection(unittest.TestCase):
    @patch('requests.post')
    @patch('src.scenarios.base_scenario.GenericScenario._reset_all_nodes')
    def test_scenario_s5_execution(self, mock_reset, mock_post):
        from src.scenarios.scenario_runner import ScenarioRunner
        
        clock = MockClock()
        runner = ScenarioRunner(clock=clock)
        runner.client = MagicMock()
        runner.client.connect = MagicMock()
        runner.client.publish = MagicMock()
        
        def simulate_events(*args, **kwargs):
            runner.collected_events.append({
                "message_type": "zone_state",
                "state": "RED",
                "is_state_clamped": False,
                "_topic": "ignis/v1/fog/zone/4B/state"
            })
            
        runner.client.publish.side_effect = simulate_events
        results = runner.run_scenario("S5", trials=1)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.scenario, "S5")
        self.assertTrue(res.passed)
        
        post_calls = mock_post.call_args_list
        self.assertGreaterEqual(len(post_calls), 1)
        args, kwargs = post_calls[0]
        self.assertIn("/api/chaos/disconnect_cloud", args[0])
        self.assertEqual(kwargs["json"]["zone_id"], "4B")
        self.assertEqual(kwargs["json"]["duration_sec"], 20)

    @patch('src.scenarios.base_scenario.GenericScenario._reset_all_nodes')
    def test_scenario_s7_concurrent_execution(self, mock_reset):
        from src.scenarios.scenario_runner import ScenarioRunner
        
        clock = MockClock()
        runner = ScenarioRunner(clock=clock)
        runner.client = MagicMock()
        runner.client.connect = MagicMock()
        runner.client.publish = MagicMock()
        
        def simulate_events(*args, **kwargs):
            runner.collected_events.append({
                "message_type": "zone_state",
                "state": "RED",
                "is_state_clamped": False,
                "_topic": "ignis/v1/fog/zone/4B/state"
            })
            
        runner.client.publish.side_effect = simulate_events
        results = runner.run_scenario("S7", trials=1)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.scenario, "S7")
        self.assertTrue(res.passed)
        self.assertIn("4A", res.zone_ids)
        self.assertIn("4B", res.zone_ids)
        
        logs_joined = " ".join(res.logs)
        self.assertIn("Starting scenario S7-4A", logs_joined)
        self.assertIn("Starting scenario S7-4B", logs_joined)

class TestMetricsCollector(unittest.TestCase):
    def test_metrics_calculation_logic(self):
        from src.metrics_collector import (
            calculate_decision_latency,
            calculate_lateral_propagation,
            calculate_false_positive_rate,
            calculate_offline_continuity,
            calculate_concurrent_zone_integrity
        )
        
        # 1. Test decision latency calculation
        mock_results_s3 = [{
            "events": [
                {
                    "message_type": "zone_state",
                    "sensor_timestamp": "2026-07-15T00:00:00Z",
                    "decision_timestamp": "2026-07-15T00:00:01.200Z",
                    "_topic": "ignis/v1/fog/zone/4B/state"
                }
            ]
        }]
        res_dl = calculate_decision_latency(mock_results_s3)
        self.assertAlmostEqual(res_dl["avg_sec"], 1.2)
        
        # 2. Test lateral propagation
        mock_results_s6 = [{
            "events": [
                {
                    "state": "RED",
                    "timestamp": "2026-07-15T00:00:00Z",
                    "_topic": "ignis/v1/fog/zone/4B/state"
                },
                {
                    "state": "YELLOW",
                    "timestamp": "2026-07-15T00:00:04.500Z",
                    "_topic": "ignis/v1/fog/zone/4C/state"
                }
            ]
        }]
        res_lp = calculate_lateral_propagation(mock_results_s6)
        self.assertAlmostEqual(res_lp["avg_propagation_sec"], 4.5)
        
        # 3. Test false positive rate
        mock_results_s4_pass = [{"events": [{"state": "YELLOW", "_topic": "ignis/v1/fog/zone/4B/state"}]}]
        mock_results_s4_fail = [{"events": [{"state": "RED", "_topic": "ignis/v1/fog/zone/4B/state"}]}]
        res_fp = calculate_false_positive_rate(mock_results_s4_pass + mock_results_s4_fail)
        self.assertEqual(res_fp["rate"], 0.5)
        self.assertEqual(res_fp["total_trials"], 2)
        
        # 4. Test offline continuity
        mock_results_s5 = [{
            "logs": ["[Offline Continuity] Action Log: ..."],
            "events": [
                {"was_buffered": True, "buffer_flush_timestamp": None},
                {"was_buffered": True, "buffer_flush_timestamp": "2026-07-15T00:00:10Z"}
            ]
        }]
        res_oc = calculate_offline_continuity(mock_results_s5)
        self.assertTrue(res_oc["uninterrupted_execution"])
        self.assertEqual(res_oc["total_enqueued"], 2)
        self.assertEqual(res_oc["flushed_count"], 1)

    @patch('matplotlib.pyplot.savefig')
    def test_report_generator(self, mock_savefig):
        from src.report_generator import generate_charts, generate_report
        
        dummy_metrics = {
            "decision_latency": {"avg_sec": 0.12, "max_sec": 0.15, "min_sec": 0.08, "all_latencies": [0.12, 0.15, 0.08, 0.14, 0.11]},
            "lateral_propagation": {"avg_propagation_sec": 3.4, "propagation_times": [3.4, 3.2, 3.6]},
            "false_positive_rate": {"rate": 0.0, "total_trials": 10, "false_positives": 0},
            "offline_continuity": {"uninterrupted_execution": True, "total_enqueued": 4, "flushed_count": 4, "flush_success_rate": 1.0},
            "concurrent_zone_integrity": {"cross_talk_detected": 0, "total_messages_processed": 100, "message_loss_pct": 0.0}
        }
        
        generate_charts(dummy_metrics, "dummy_charts_dir")
        self.assertEqual(mock_savefig.call_count, 5)
        
        with patch('builtins.open', mock_open()) as mock_file:
            generate_report(dummy_metrics, "dummy_report.md")
            mock_file.assert_called_with("dummy_report.md", 'w')
            handle = mock_file()
            handle.write.assert_called_once()

class TestDashboardMetrics(unittest.TestCase):
    @patch('src.cloud_dashboard.app.CloudDashboardDB.connect')
    @patch('src.cloud_dashboard.app.CloudDashboardDB.close')
    def test_dashboard_metrics_routes(self, mock_close, mock_connect):
        from fastapi.testclient import TestClient
        from src.cloud_dashboard.app import app
        
        with TestClient(app) as client:
            res = client.get("/api/metrics/latest")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("decision_latency", data)
            self.assertIn("false_positive_rate", data)
            
            res_ui = client.get("/metrics")
            self.assertEqual(res_ui.status_code, 200)
            self.assertIn("IGNIS", res_ui.text)

if __name__ == '__main__':
    unittest.main()
