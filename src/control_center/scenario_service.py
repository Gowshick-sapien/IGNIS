import os
import sys
import json
import time
import logging
import threading
import paho.mqtt.client as mqtt

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.scenario import ScenarioGenerator

logger = logging.getLogger("scenario_service")

class ScenarioService:
    """Orchestrates test scenarios by sending step-by-step MQTT override commands to Edge Nodes."""
    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883, zone_id: str = "4B"):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.zone_id = zone_id
        
        if self.zone_id == "4A":
            self.active_nodes = ["4A-E1", "4A-E2", "4A-E3"]
        elif self.zone_id == "4B":
            self.active_nodes = ["4B-E1", "4B-E2", "4B-E3"]
        elif self.zone_id == "4C":
            self.active_nodes = ["4C-E1", "4C-E2", "4C-E3"]
        else:
            self.active_nodes = ["E11", "E12", "E13"]
        self.current_thread = None
        self.stop_event = threading.Event()
        self.running_scenario = None
        self.current_step = 0
        self.total_steps = 0
        
        # Internal client for publishing control messages
        self.client = mqtt.Client(client_id="ignis_scenario_orchestrator")
        
    def connect(self):
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            logger.info("Scenario Service connected to MQTT broker.")
        except Exception as e:
            logger.error(f"Scenario Service failed to connect to MQTT: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Scenario Service disconnected.")

    def start_scenario(self, scenario_id: str) -> bool:
        """Starts a scenario in a background thread."""
        if self.current_thread and self.current_thread.is_alive():
            logger.warning("A scenario is already running. Stopping it first.")
            self.stop_scenario()
            
        self.stop_event.clear()
        self.running_scenario = scenario_id
        self.current_step = 0
        
        if scenario_id == "S1":
            steps = ScenarioGenerator.get_normal_day_scenario()
            target = self._run_global_scenario
        elif scenario_id == "S2":
            steps = ScenarioGenerator.get_slow_building_risk_scenario()
            target = self._run_global_scenario
        elif scenario_id == "S3":
            steps = ScenarioGenerator.get_sudden_ignition_scenario()
            target = self._run_localized_scenario
        elif scenario_id == "S4":
            steps = ScenarioGenerator.get_single_sensor_fault_scenario()
            target = self._run_localized_scenario
        elif scenario_id == "S6":
            steps = ScenarioGenerator.get_lateral_spread_scenario()
            target = self._run_global_scenario
        else:
            logger.error(f"Unknown scenario ID: {scenario_id}")
            return False
            
        self.total_steps = len(steps)
        self.current_thread = threading.Thread(target=target, args=(scenario_id, steps))
        self.current_thread.daemon = True
        self.current_thread.start()
        logger.info(f"Started scenario {scenario_id} thread.")
        return True

    def stop_scenario(self):
        """Stops the currently running scenario and resets nodes to baseline."""
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            self.current_thread.join(timeout=5)
        
        self.running_scenario = None
        self.current_step = 0
        self.total_steps = 0
        
        # Reset all nodes back to baseline
        self._reset_all_nodes()
        logger.info("Scenario execution stopped and reset to baseline.")

    def get_status(self) -> dict:
        """Returns the current state of the orchestrator."""
        return {
            "running_scenario": self.running_scenario,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "is_active": self.current_thread is not None and self.current_thread.is_alive()
        }

    def _reset_all_nodes(self):
        for node in self.active_nodes:
            control_topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{node}/control"
            payload = {
                "message_type": "control",
                "version": "1",
                "command": "set_mode",
                "mode": "baseline"
            }
            self.client.publish(control_topic, json.dumps(payload))

    def _run_global_scenario(self, scenario_id: str, steps: list):
        """Runs scenarios that affect all nodes in the zone (S1, S2)."""
        logger.info(f"Running global scenario {scenario_id} ({len(steps)} steps)")
        
        try:
            # Put all nodes in scenario mode
            for step_idx, step in enumerate(steps):
                if self.stop_event.is_set():
                    break
                    
                self.current_step = step_idx + 1
                sensor_data = step["sensor_data"]
                seasonal_baseline = step["seasonal_baseline"]
                
                logger.info(f"Publishing Step {self.current_step}/{self.total_steps} for global scenario {scenario_id}")
                
                for node in self.active_nodes:
                    control_topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{node}/control"
                    payload = {
                        "message_type": "control",
                        "version": "1",
                        "command": "set_mode",
                        "mode": "scenario",
                        "sensor_data": sensor_data,
                        "seasonal_baseline": seasonal_baseline
                    }
                    self.client.publish(control_topic, json.dumps(payload))
                    
                # Wait 4 seconds (slightly longer than edge tick rate to allow update processing)
                time.sleep(4)
                
            logger.info(f"Global scenario {scenario_id} completed.")
        except Exception as e:
            logger.error(f"Error in global scenario runner: {e}")
        finally:
            self._reset_all_nodes()
            self.running_scenario = None

    def _run_localized_scenario(self, scenario_id: str, steps: list):
        """Runs scenarios that affect a specific localized node (middle node in active_nodes), keeping others in baseline (S3, S4)."""
        target_node = self.active_nodes[1]
        baseline_node_1 = self.active_nodes[0]
        baseline_node_2 = self.active_nodes[2]
        
        logger.info(f"Running localized scenario {scenario_id} on {target_node} ({len(steps)} steps)")
        
        try:
            # Ensure other nodes are in baseline
            control_topic_b1 = f"ignis/v1/system/zone/{self.zone_id}/edge/{baseline_node_1}/control"
            control_topic_b2 = f"ignis/v1/system/zone/{self.zone_id}/edge/{baseline_node_2}/control"
            self.client.publish(control_topic_b1, json.dumps({"message_type": "control", "version": "1", "command": "set_mode", "mode": "baseline"}))
            self.client.publish(control_topic_b2, json.dumps({"message_type": "control", "version": "1", "command": "set_mode", "mode": "baseline"}))
            
            control_topic_target = f"ignis/v1/system/zone/{self.zone_id}/edge/{target_node}/control"
            
            for step_idx, step in enumerate(steps):
                if self.stop_event.is_set():
                    break
                    
                self.current_step = step_idx + 1
                sensor_data = step["sensor_data"]
                seasonal_baseline = step["seasonal_baseline"]
                
                logger.info(f"Publishing Step {self.current_step}/{self.total_steps} for localized node {target_node}")
                
                payload = {
                    "message_type": "control",
                    "version": "1",
                    "command": "set_mode",
                    "mode": "scenario",
                    "sensor_data": sensor_data,
                    "seasonal_baseline": seasonal_baseline
                }
                if scenario_id == "S4" and step_idx >= 2:
                    # S4 simulates a gas sensor fault. In scenario.py, the gas_ppm is spiked in sensor_data.
                    # We can use the 'fault' mode command, or just publish spiked sensor_data.
                    # Since ScenarioGenerator.get_single_sensor_fault_scenario() already spikes gas_ppm in steps,
                    # passing it as a scenario reading works perfectly. 
                    # We can also explicitly trigger 'fault' command to test the node's FaultInjectionProvider!
                    # Let's use the 'fault' command format to fully exercise the edge node's FaultInjectionProvider:
                    payload = {
                        "message_type": "control",
                        "version": "1",
                        "command": "set_mode",
                        "mode": "fault",
                        "fault_sensor": "gas_ppm",
                        "fault_value": 100.0
                    }
                    
                self.client.publish(control_topic_target, json.dumps(payload))
                
                time.sleep(4)
                
            logger.info(f"Localized scenario {scenario_id} completed.")
        except Exception as e:
            logger.error(f"Error in localized scenario runner: {e}")
        finally:
            self._reset_all_nodes()
            self.running_scenario = None
