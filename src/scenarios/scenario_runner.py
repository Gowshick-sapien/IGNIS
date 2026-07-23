import os
import glob
import json
import yaml
import logging
import paho.mqtt.client as mqtt
from typing import List
from src.clock import default_clock
from src.scenarios.results import ScenarioResult, ScenarioMetric

logger = logging.getLogger("scenario_runner")

class ScenarioRunner:
    def __init__(self, mqtt_host="localhost", mqtt_port=1883, clock=default_clock):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.clock = clock
        self.collected_events = []
        self.client = mqtt.Client(client_id="ignis_scenario_runner")
        self.client.on_message = self.on_message

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            payload["_topic"] = msg.topic
            self.collected_events.append(payload)
        except Exception:
            pass

    def run_scenario(self, scenario_id: str, trials: int = 1, seed: int = None) -> List[ScenarioResult]:
        from src.scenarios.scenario_registry import SCENARIO_REGISTRY
        scenario_class = SCENARIO_REGISTRY.get(scenario_id)
        if not scenario_class:
            raise ValueError(f"Scenario {scenario_id} not registered.")

        digit = scenario_id[1]
        matches = glob.glob(f"scenarios/s{digit}_*.yaml")
        yaml_path = matches[0] if matches else f"scenarios/s{digit.lower()}_sensor_fault.yaml"

        with open(yaml_path, 'r') as f:
            yaml_data = yaml.safe_load(f)

        target_info = yaml_data.get("target", {})
        zone_ids = target_info.get("zone_ids", ["4B"])
        expected_outcome = yaml_data.get("expected_outcome", {})

        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()

        # Subscribe to all fog node publications
        self.client.subscribe("ignis/v1/fog/zone/#")

        results = []
        for trial in range(trials):
            self.collected_events = []
            
            scenario_instance = scenario_class()
            scenario_instance.yaml_path = yaml_path
            if seed is not None:
                scenario_instance.seed = seed + trial
            
            start_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
            start_epoch = self.clock.time()
            
            # Setup
            primary_zone = zone_ids[0] if zone_ids else "4B"
            scenario_instance.setup(self.client, primary_zone, self.clock)
            
            # Run
            try:
                result = scenario_instance.run()
            except Exception as e:
                result = ScenarioResult(
                    scenario=scenario_id,
                    passed=False,
                    duration_sec=self.clock.time() - start_epoch,
                    start_time=start_time,
                    end_time=self.clock.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    metrics=[],
                    events=[],
                    logs=["Error during scenario run"],
                    errors=[str(e)],
                    zone_ids=zone_ids,
                    trial_index=trial
                )

            # Teardown
            scenario_instance.teardown()
            
            # Capture collected events during execution
            self.clock.sleep(0.5)
            
            if not result.events:
                result.events = self.collected_events

            # Deterministic stable sort of events
            import hashlib
            def event_sort_key(e: dict):
                ts = e.get("timestamp") or e.get("sensor_timestamp") or e.get("decision_timestamp") or ""
                zone_id = e.get("zone_id") or ""
                msg_type = e.get("message_type") or ""
                node_id = e.get("node_id") or ""
                topic = e.get("_topic") or ""
                
                # Serialized payload hash as tie-breaker
                try:
                    serialized = json.dumps(e, sort_keys=True)
                except Exception:
                    serialized = str(e)
                payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                
                return (trial, scenario_id, ts, zone_id, msg_type, node_id, topic, payload_hash)
            
            result.events.sort(key=event_sort_key)

            # Validate expected outcomes if they are defined
            if expected_outcome:
                passed = self.validate_outcome(result.events, expected_outcome)
                result.passed = passed
                
                # Add is_clamped metric based on expectations
                is_clamped_expected = expected_outcome.get("is_clamped", False)
                state_events = [e for e in result.events if "state" in e.get("_topic", "")]
                actual_clamped = any(e.get("is_state_clamped", False) for e in state_events)
                passed_clamped = (actual_clamped == is_clamped_expected)
                
                metric = ScenarioMetric(
                    name="is_clamped",
                    value=float(actual_clamped),
                    unit="bool",
                    passed=passed_clamped,
                    threshold=float(is_clamped_expected),
                    details=f"Expected clamped={is_clamped_expected}, got clamped={actual_clamped}"
                )
                result.metrics.append(metric)
            
            result.trial_index = trial
            results.append(result)

        self.client.loop_stop()
        self.client.disconnect()
        return results

    def validate_outcome(self, events: List[dict], expected: dict) -> bool:
        state_events = [e for e in events if "state" in e.get("_topic", "")]
        if not state_events:
            return False
            
        final_state = state_events[-1].get("state", "GREEN")
        expected_final = expected.get("final_state", "GREEN")
        
        max_state_allowed = expected.get("max_state_allowed", "RED")
        is_clamped_expected = expected.get("is_clamped", False)
        
        state_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
        
        # Check final state
        if final_state != expected_final:
            return False
            
        # Check max state allowed
        for event in state_events:
            state = event.get("state", "GREEN")
            if state_order.get(state, 0) > state_order.get(max_state_allowed, 3):
                return False
                
        # Check clamping
        actual_clamped = any(e.get("is_state_clamped", False) for e in state_events)
        if actual_clamped != is_clamped_expected:
            return False
            
        return True
