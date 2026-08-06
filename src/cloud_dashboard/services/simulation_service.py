import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Optional
import paho.mqtt.client as mqtt

# Add root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.scenario import ScenarioGenerator

logger = logging.getLogger("simulation_service")


class SimulationService:
    """
    Multi-Zone Scenario Orchestrator for the Cloud NOC Dashboard.
    Enables operators to inject simulation scenarios (S1-S4, S6) into any zone (4A, 4B, 4C)
    independently or concurrently by routing MQTT control commands to the respective edge nodes.
    """

    DEFAULT_ZONE_NODES: Dict[str, List[str]] = {
        "4A": ["4A-E1", "4A-E2", "4A-E3"],
        "4B": ["4B-E1", "4B-E2", "4B-E3"],
        "4C": ["4C-E1", "4C-E2", "4C-E3"],
    }

    def __init__(self):
        # Broker configuration map per zone
        self.zone_brokers: Dict[str, Dict[str, any]] = {
            "4A": {
                "hosts": [
                    os.environ.get("ZONE_4A_MQTT_HOST", "mqtt-broker-4a"),
                    os.environ.get("LOCAL_MQTT_HOST_4A", "localhost"),
                    "localhost"
                ],
                "ports": [
                    int(os.environ.get("ZONE_4A_MQTT_PORT_INTERNAL", 1883)),
                    int(os.environ.get("ZONE_4A_MQTT_PORT", 1881))
                ]
            },
            "4B": {
                "hosts": [
                    os.environ.get("ZONE_4B_MQTT_HOST", "mqtt-broker-4b"),
                    os.environ.get("LOCAL_MQTT_HOST_4B", os.environ.get("LOCAL_MQTT_HOST", "localhost")),
                    "localhost"
                ],
                "ports": [
                    int(os.environ.get("ZONE_4B_MQTT_PORT_INTERNAL", 1883)),
                    int(os.environ.get("ZONE_4B_MQTT_PORT", 1883))
                ]
            },
            "4C": {
                "hosts": [
                    os.environ.get("ZONE_4C_MQTT_HOST", "mqtt-broker-4c"),
                    os.environ.get("LOCAL_MQTT_HOST_4C", "localhost"),
                    "localhost"
                ],
                "ports": [
                    int(os.environ.get("ZONE_4C_MQTT_PORT_INTERNAL", 1883)),
                    int(os.environ.get("ZONE_4C_MQTT_PORT", 1885))
                ]
            },
        }

        # Central cloud broker
        self.cloud_broker_host = os.environ.get("CLOUD_MQTT_HOST", "localhost")
        self.cloud_broker_port = int(os.environ.get("CLOUD_MQTT_PORT", 1884))

        # Per-zone state tracker
        self.zone_states: Dict[str, dict] = {
            "4A": self._create_initial_state("4A"),
            "4B": self._create_initial_state("4B"),
            "4C": self._create_initial_state("4C"),
        }

        # Locks per zone for thread-safe operations
        self._zone_locks: Dict[str, threading.Lock] = {
            "4A": threading.Lock(),
            "4B": threading.Lock(),
            "4C": threading.Lock(),
        }

    def _create_initial_state(self, zone_id: str) -> dict:
        return {
            "zone_id": zone_id,
            "running_scenario": None,
            "current_step": 0,
            "total_steps": 0,
            "status": "idle",
            "is_active": False,
            "error": None,
            "stop_event": threading.Event(),
            "thread": None,
            "start_time": None
        }

    def _publish_control(self, zone_id: str, node_id: str, payload: dict):
        """
        Publishes an MQTT control payload to the appropriate zone broker,
        with fallback to cloud broker.
        """
        control_topic = f"ignis/v1/system/zone/{zone_id}/edge/{node_id}/control"
        data = json.dumps(payload)
        published = False

        # 1. Try zone-specific brokers
        broker_cfg = self.zone_brokers.get(zone_id, {})
        hosts = broker_cfg.get("hosts", ["localhost"])
        ports = broker_cfg.get("ports", [1883])

        client_id = f"sim_pub_{zone_id}_{node_id}_{int(time.time()*1000)%10000}"
        
        for host in hosts:
            for port in ports:
                try:
                    c = mqtt.Client(client_id=client_id)
                    c.connect(host, port, keepalive=5)
                    c.publish(control_topic, data, qos=1)
                    c.disconnect()
                    published = True
                    break
                except Exception:
                    continue
            if published:
                break

        # 2. Also publish to cloud broker as redundant broadcast
        try:
            c = mqtt.Client(client_id=f"{client_id}_cloud")
            c.connect(self.cloud_broker_host, self.cloud_broker_port, keepalive=5)
            c.publish(control_topic, data, qos=1)
            c.disconnect()
        except Exception:
            pass

        if not published:
            logger.warning(f"Could not connect to zone {zone_id} broker to publish to {control_topic}")

    def _reset_all_nodes_in_zone(self, zone_id: str):
        """Resets all edge nodes in the given zone to baseline."""
        nodes = self.DEFAULT_ZONE_NODES.get(zone_id, [f"{zone_id}-E1", f"{zone_id}-E2", f"{zone_id}-E3"])
        payload = {
            "message_type": "control",
            "version": "1",
            "command": "set_mode",
            "mode": "baseline"
        }
        for node in nodes:
            self._publish_control(zone_id, node, payload)
        logger.info(f"All nodes in Zone {zone_id} reset to baseline.")

    def start_scenario(self, zone_id: str, scenario_id: str) -> dict:
        """
        Starts a simulation scenario on the specified zone in a background thread.
        Supported scenarios: S1, S2, S3, S4, S6
        """
        zone_id = zone_id.upper()
        if zone_id not in self.zone_states:
            return {"status": "error", "message": f"Unsupported zone '{zone_id}'. Supported zones: {list(self.zone_states.keys())}"}

        with self._zone_locks[zone_id]:
            state = self.zone_states[zone_id]

            # If already running, stop previous first
            if state["thread"] and state["thread"].is_alive():
                logger.info(f"Stopping previous scenario on zone {zone_id} before starting {scenario_id}")
                state["stop_event"].set()
                state["thread"].join(timeout=3)

            state["stop_event"].clear()
            state["running_scenario"] = scenario_id
            state["current_step"] = 0
            state["status"] = "running"
            state["is_active"] = True
            state["error"] = None
            state["start_time"] = time.time()

            # Determine steps & runner
            if scenario_id == "S1":
                steps = ScenarioGenerator.get_normal_day_scenario()
                target_func = self._run_global_scenario
            elif scenario_id == "S2":
                steps = ScenarioGenerator.get_slow_building_risk_scenario()
                target_func = self._run_global_scenario
            elif scenario_id == "S3":
                steps = ScenarioGenerator.get_sudden_ignition_scenario()
                target_func = self._run_localized_scenario
            elif scenario_id == "S4":
                steps = ScenarioGenerator.get_single_sensor_fault_scenario()
                target_func = self._run_localized_scenario
            elif scenario_id == "S6":
                steps = ScenarioGenerator.get_lateral_spread_scenario()
                target_func = self._run_global_scenario
            else:
                state["status"] = "error"
                state["is_active"] = False
                state["error"] = f"Unknown scenario: {scenario_id}"
                return {"status": "error", "message": state["error"], "zone_id": zone_id}

            state["total_steps"] = len(steps)
            thread = threading.Thread(
                target=target_func,
                args=(zone_id, scenario_id, steps),
                daemon=True,
                name=f"sim_{zone_id}_{scenario_id}"
            )
            state["thread"] = thread
            thread.start()

            logger.info(f"Simulation {scenario_id} started on Zone {zone_id} ({len(steps)} steps)")
            return {
                "status": "started",
                "zone_id": zone_id,
                "scenario_id": scenario_id,
                "total_steps": len(steps)
            }

    def stop_scenario(self, zone_id: str) -> dict:
        """Stops the running scenario on the specified zone and resets all nodes to baseline."""
        zone_id = zone_id.upper()
        if zone_id not in self.zone_states:
            return {"status": "error", "message": f"Unknown zone: {zone_id}"}

        with self._zone_locks[zone_id]:
            state = self.zone_states[zone_id]
            if state["thread"] and state["thread"].is_alive():
                state["stop_event"].set()
                state["thread"].join(timeout=4)

            state["running_scenario"] = None
            state["current_step"] = 0
            state["total_steps"] = 0
            state["status"] = "idle"
            state["is_active"] = False
            state["thread"] = None

            # Reset all nodes in zone to baseline mode
            self._reset_all_nodes_in_zone(zone_id)
            logger.info(f"Simulation stopped and Zone {zone_id} reset to baseline.")
            return {"status": "stopped", "zone_id": zone_id}

    def stop_all(self):
        """Stops all running scenarios across all zones."""
        for zone_id in list(self.zone_states.keys()):
            self.stop_scenario(zone_id)

    def get_status(self, zone_id: str) -> dict:
        """Returns the current scenario status for a single zone."""
        zone_id = zone_id.upper()
        if zone_id not in self.zone_states:
            return {
                "zone_id": zone_id,
                "running_scenario": None,
                "current_step": 0,
                "total_steps": 0,
                "status": "idle",
                "is_active": False,
                "progress_pct": 0
            }

        state = self.zone_states[zone_id]
        total = state.get("total_steps", 0)
        curr = state.get("current_step", 0)
        pct = int((curr / total * 100)) if total > 0 else 0

        return {
            "zone_id": zone_id,
            "running_scenario": state.get("running_scenario"),
            "current_step": curr,
            "total_steps": total,
            "status": state.get("status", "idle"),
            "is_active": state.get("is_active", False) and (state["thread"] is not None and state["thread"].is_alive()),
            "progress_pct": pct,
            "error": state.get("error")
        }

    def get_all_status(self) -> List[dict]:
        """Returns status for all known zones."""
        return [self.get_status(z) for z in ["4A", "4B", "4C"]]

    def _run_global_scenario(self, zone_id: str, scenario_id: str, steps: list):
        """Runs a scenario that applies to all edge nodes in the zone simultaneously (S1, S2, S6)."""
        nodes = self.DEFAULT_ZONE_NODES.get(zone_id, [f"{zone_id}-E1", f"{zone_id}-E2", f"{zone_id}-E3"])
        state = self.zone_states[zone_id]

        try:
            for step_idx, step in enumerate(steps):
                if state["stop_event"].is_set():
                    logger.info(f"Stop signal received during global scenario {scenario_id} on Zone {zone_id}")
                    break

                state["current_step"] = step_idx + 1
                sensor_data = step["sensor_data"]
                seasonal_baseline = step["seasonal_baseline"]

                logger.info(f"[Zone {zone_id}] Publishing Step {state['current_step']}/{state['total_steps']} for {scenario_id}")

                for node in nodes:
                    payload = {
                        "message_type": "control",
                        "version": "1",
                        "command": "set_mode",
                        "mode": "scenario",
                        "sensor_data": sensor_data,
                        "seasonal_baseline": seasonal_baseline
                    }
                    self._publish_control(zone_id, node, payload)

                # Wait 4 seconds between steps to allow sensor tick & processing
                for _ in range(40):
                    if state["stop_event"].is_set():
                        break
                    time.sleep(0.1)

            logger.info(f"Global scenario {scenario_id} completed on Zone {zone_id}")
            state["status"] = "completed"
        except Exception as e:
            logger.error(f"Error in global scenario {scenario_id} on Zone {zone_id}: {e}")
            state["status"] = "error"
            state["error"] = str(e)
        finally:
            self._reset_all_nodes_in_zone(zone_id)
            state["is_active"] = False
            state["running_scenario"] = None

    def _run_localized_scenario(self, zone_id: str, scenario_id: str, steps: list):
        """
        Runs scenarios that affect a localized edge node (middle node, e.g. 4B-E2),
        keeping neighbor nodes in baseline (S3, S4).
        """
        nodes = self.DEFAULT_ZONE_NODES.get(zone_id, [f"{zone_id}-E1", f"{zone_id}-E2", f"{zone_id}-E3"])
        target_node = nodes[1] if len(nodes) > 1 else nodes[0]
        baseline_nodes = [n for n in nodes if n != target_node]
        state = self.zone_states[zone_id]

        try:
            # Ensure other nodes are in baseline mode
            for b_node in baseline_nodes:
                self._publish_control(zone_id, b_node, {
                    "message_type": "control",
                    "version": "1",
                    "command": "set_mode",
                    "mode": "baseline"
                })

            for step_idx, step in enumerate(steps):
                if state["stop_event"].is_set():
                    logger.info(f"Stop signal received during localized scenario {scenario_id} on Zone {zone_id}")
                    break

                state["current_step"] = step_idx + 1
                sensor_data = step["sensor_data"]
                seasonal_baseline = step["seasonal_baseline"]

                logger.info(f"[Zone {zone_id}] Publishing Step {state['current_step']}/{state['total_steps']} for {scenario_id} on {target_node}")

                payload = {
                    "message_type": "control",
                    "version": "1",
                    "command": "set_mode",
                    "mode": "scenario",
                    "sensor_data": sensor_data,
                    "seasonal_baseline": seasonal_baseline
                }

                # If S4 (single sensor fault), inject fault mode on step 2+
                if scenario_id == "S4" and step_idx >= 2:
                    payload = {
                        "message_type": "control",
                        "version": "1",
                        "command": "set_mode",
                        "mode": "fault",
                        "fault_sensor": "gas_ppm",
                        "fault_value": 100.0
                    }

                self._publish_control(zone_id, target_node, payload)

                for _ in range(40):
                    if state["stop_event"].is_set():
                        break
                    time.sleep(0.1)

            logger.info(f"Localized scenario {scenario_id} completed on Zone {zone_id}")
            state["status"] = "completed"
        except Exception as e:
            logger.error(f"Error in localized scenario {scenario_id} on Zone {zone_id}: {e}")
            state["status"] = "error"
            state["error"] = str(e)
        finally:
            self._reset_all_nodes_in_zone(zone_id)
            state["is_active"] = False
            state["running_scenario"] = None
