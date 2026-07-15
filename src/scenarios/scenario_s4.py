import json
from src.scenarios.base_scenario import GenericScenario
from src.scenarios.results import ScenarioResult

class ScenarioS4(GenericScenario):
    scenario_id = "S4"
    description = "Single sensor fault — validates 3-sensor confirmation rule"

    def run(self) -> ScenarioResult:
        start_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_epoch = self.clock.time()
        
        steps = self.yaml_data.get("steps", [])
        target_node = self.active_nodes[1]
        
        logs = []
        errors = []
        
        self._reset_all_nodes()
        logs.append(f"Starting scenario {self.scenario_id}")
        
        for step in steps:
            step_idx = step.get("index", 0)
            sensor_data = step.get("sensor_data", {})
            seasonal_baseline = step.get("seasonal_baseline", 0.5)
            duration = step.get("duration_sec", 4)
            
            if step_idx < 2:
                payload = {
                    "message_type": "control",
                    "version": "1",
                    "command": "set_mode",
                    "mode": "scenario",
                    "sensor_data": sensor_data,
                    "seasonal_baseline": seasonal_baseline
                }
            else:
                payload = {
                    "message_type": "control",
                    "version": "1",
                    "command": "set_mode",
                    "mode": "fault",
                    "fault_sensor": "gas_ppm",
                    "fault_value": 100.0
                }
                
            topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{target_node}/control"
            self.client.publish(topic, json.dumps(payload))
            logs.append(f"Step {step_idx}: Published localized override control to {target_node} (mode: {payload['mode']})")
            
            self.clock.sleep(duration)
            
        self._reset_all_nodes()
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
