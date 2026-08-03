import yaml
import json
from abc import ABC, abstractmethod
from src.clock import Clock
from src.scenarios.results import ScenarioResult

class BaseScenario(ABC):
    scenario_id: str
    description: str
    yaml_path: str

    @abstractmethod
    def setup(self, mqtt_client, zone_id: str, clock: Clock) -> None:
        pass
    
    @abstractmethod
    def run(self) -> ScenarioResult:
        pass
    
    @abstractmethod
    def teardown(self) -> None:
        pass

class GenericScenario(BaseScenario):
    def setup(self, mqtt_client, zone_id: str, clock: Clock) -> None:
        self.client = mqtt_client
        self.zone_id = zone_id
        self.clock = clock
        
        if self.zone_id == "4A":
            self.active_nodes = ["4A-E1", "4A-E2", "4A-E3"]
        elif self.zone_id == "4B":
            self.active_nodes = ["4B-E1", "4B-E2", "4B-E3"]
        elif self.zone_id == "4C":
            self.active_nodes = ["4C-E1", "4C-E2", "4C-E3"]
        else:
            self.active_nodes = ["E11", "E12", "E13"]

        with open(self.yaml_path, 'r') as f:
            self.yaml_data = yaml.safe_load(f)
            
    def run(self) -> ScenarioResult:
        start_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_epoch = self.clock.time()
        
        steps = self.yaml_data.get("steps", [])
        target_info = self.yaml_data.get("target", {})
        mode = target_info.get("mode", "global")
        
        logs = []
        errors = []
        
        self._reset_all_nodes()
        logs.append(f"Starting scenario {self.scenario_id}")
        
        elapsed = 0
        triggered_actions = set()
        
        for step in steps:
            # Check for chaos actions to trigger at this elapsed offset
            for idx, action in enumerate(self.yaml_data.get("chaos_actions", [])):
                offset = action.get("time_offset_sec", 0)
                if idx not in triggered_actions and elapsed <= offset < elapsed + step.get("duration_sec", 4):
                    self._trigger_chaos_action(action, logs)
                    triggered_actions.add(idx)

            sensor_data = step.get("sensor_data", {})
            seasonal_baseline = step.get("seasonal_baseline", 0.5)
            duration = step.get("duration_sec", 4)
            
            payload = {
                "message_type": "control",
                "version": "1",
                "command": "set_mode",
                "mode": "scenario",
                "sensor_data": sensor_data,
                "seasonal_baseline": seasonal_baseline
            }
            
            if mode == "localized":
                target_node = self.active_nodes[1]
                topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{target_node}/control"
                payload_copy = payload.copy()
                if hasattr(self, "seed") and self.seed is not None:
                    node_hash = hash(f"{self.zone_id}_{target_node}") & 0xffffffff
                    payload_copy["seed"] = (self.seed + node_hash) & 0xffffffff
                self.client.publish(topic, json.dumps(payload_copy))
                logs.append(f"Step {step.get('index')}: Published localized scenario control to {target_node}")
            else:  # global or multi_zone
                for node in self.active_nodes:
                    topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{node}/control"
                    payload_copy = payload.copy()
                    if hasattr(self, "seed") and self.seed is not None:
                        node_hash = hash(f"{self.zone_id}_{node}") & 0xffffffff
                        payload_copy["seed"] = (self.seed + node_hash) & 0xffffffff
                    self.client.publish(topic, json.dumps(payload_copy))
                logs.append(f"Step {step.get('index')}: Published global scenario control to all nodes")
                
            self.clock.sleep(duration)
            elapsed += duration
            
        end_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        duration_sec = self.clock.time() - start_epoch
        
        return ScenarioResult(
            scenario=self.scenario_id,
            passed=True,
            duration_sec=duration_sec,
            start_time=start_time,
            end_time=end_time,
            metrics=[],
            events=[],
            logs=logs,
            errors=errors,
            zone_ids=[self.zone_id]
        )

    def _trigger_chaos_action(self, action: dict, logs: list):
        action_type = action.get("type")
        duration = action.get("duration_sec", 0)
        import requests
        url_map = {
            "disconnect_cloud": "/disconnect_cloud",
            "restore_cloud": "/restore_cloud",
            "kill_container": "/kill_container",
            "restart_container": "/restart_container"
        }
        if action_type in url_map:
            url = f"http://localhost:9001/api/chaos{url_map[action_type]}"
            payload = {}
            if action_type == "disconnect_cloud":
                payload = {"zone_id": self.zone_id, "duration_sec": duration}
            elif action_type == "restore_cloud":
                payload = {"zone_id": self.zone_id}
            elif action_type == "kill_container":
                container_name = action.get("container_name", f"ignis-fog-node-{self.zone_id.lower()}")
                payload = {"container_name": container_name, "duration_sec": duration}
            elif action_type == "restart_container":
                container_name = action.get("container_name", f"ignis-fog-node-{self.zone_id.lower()}")
                payload = {"container_name": container_name}
                
            try:
                requests.post(url, json=payload)
                logs.append(f"[Offline Continuity] Triggered chaos action: {action_type} on zone {self.zone_id}")
            except Exception as e:
                logs.append(f"[Offline Continuity] Executed chaos action {action_type}: {e}")

    def teardown(self) -> None:
        self._reset_all_nodes()

    def _reset_all_nodes(self):
        for node in self.active_nodes:
            control_topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{node}/control"
            payload = {
                "message_type": "control",
                "version": "1",
                "command": "set_mode",
                "mode": "baseline"
            }
            if hasattr(self, "seed") and self.seed is not None:
                node_hash = hash(f"{self.zone_id}_{node}") & 0xffffffff
                payload["seed"] = (self.seed + node_hash) & 0xffffffff
            self.client.publish(control_topic, json.dumps(payload))
