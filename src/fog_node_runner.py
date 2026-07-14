import os
import sys
import json
import time
import calendar
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load .env configurations if available (useful for local host testing)
load_dotenv()

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fog_node import FogNode

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fog_node_runner")

class FogNodeRunner:
    """Manages the Fog Node service daemon, communicating with both Local and Cloud Brokers."""
    STATE_ORDER = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    
    def __init__(self):
        # 1. Fetch Configuration from Environment (initialized from .env)
        self.zone_id = os.environ.get("ZONE_ID", "4B")
        
        # Local Broker Connection
        self.local_host = os.environ.get("LOCAL_MQTT_HOST", "localhost")
        self.local_port = int(os.environ.get("LOCAL_MQTT_PORT", 1883))
        
        # Cloud Broker Connection
        self.cloud_host = os.environ.get("CLOUD_MQTT_HOST", "localhost")
        self.cloud_port = int(os.environ.get("CLOUD_MQTT_PORT", 1884))
        
        config_path = os.environ.get("CONFIG_PATH", os.path.join("config", "zones_config.json"))
        self.config = self.load_config(config_path)
        
        # 2. Instantiate local decision processor
        self.fog_processor = FogNode(self.zone_id, self.config)
        
        # Telemetry & State caches
        self.node_states = {}       # node_id -> decision_record
        self.last_zone_state = "GREEN"
        
        # 3. Advisory Override States
        self.override_active = False
        self.override_state = "NONE"
        self.override_operator = "SYSTEM"
        self.override_actions = []
        self.override_reason = ""
        
        # 4. Command Security Cache
        self.processed_command_ids = set()
        self.last_sequence_number = -1
        
        # 5. Initialize MQTT Clients
        self.client_local = mqtt.Client(client_id=f"fog_node_local_{self.zone_id}")
        self.client_local.on_connect = self.on_connect_local
        self.client_local.on_message = self.on_message_local
        
        self.client_cloud = mqtt.Client(client_id=f"fog_node_cloud_{self.zone_id}")
        self.client_cloud.on_connect = self.on_connect_cloud
        self.client_cloud.on_message = self.on_message_cloud
        
        # 6. Lateral Coordination State
        self.neighbors = self.config.get("neighbors", [])
        self.lateral_warning_timeout = self.config.get("lateral_warning_timeout_sec", 30)
        self.active_lateral_warnings = {}  # zone_id -> {"zone_id": str, "state": str, "timestamp": float}
        self.lateral_preemptive_active = False
        
    def load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, 'r') as f:
            full_config = json.load(f)
        defaults = full_config.get("defaults", {})
        zone_data = full_config.get("zones", {}).get(self.zone_id, {})
        # Merge: zone-specific overrides take precedence over defaults
        config = {**defaults, **zone_data}
        config["zone_id"] = self.zone_id
        return config

    # ==========================================
    # Local MQTT Callbacks
    # ==========================================
    def on_connect_local(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to LOCAL MQTT broker at {self.local_host}:{self.local_port}")
            # Subscribe to local edge node readings: ignis/v1/telemetry/zone/{zone}/edge/+
            telemetry_topic = f"ignis/v1/telemetry/zone/{self.zone_id}/edge/+"
            self.client_local.subscribe(telemetry_topic)
            logger.info(f"Subscribed to Local readings topic: {telemetry_topic}")
        else:
            logger.error(f"Failed to connect to LOCAL MQTT broker, code: {rc}")

    def on_message_local(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            node_id = payload.get("node_id")
            if not node_id:
                logger.warning("Received local telemetry payload without node_id.")
                return
                
            # A. Process telemetry using FogNode decision logic
            decision_record = self.fog_processor.process_reading(payload)
            self.node_states[node_id] = decision_record
            
            logger.info(f"Ingested E-Node {node_id} Telemetry | Local State: {decision_record['state']} (WHI: {decision_record['whi']:.3f})")
            
            # B. Dual Reporting: Forward raw telemetry to the Cloud Broker
            # Topic: ignis/v1/telemetry/zone/{zone_id}/edge/{node_id}
            cloud_telemetry_topic = f"ignis/v1/telemetry/zone/{self.zone_id}/edge/{node_id}"
            self.client_cloud.publish(cloud_telemetry_topic, json.dumps(payload))
            
            # C. Aggregate and Publish Zone Status
            self.evaluate_and_publish_zone_status()
            
        except Exception as e:
            logger.error(f"Error processing local MQTT message: {e}")

    # ==========================================
    # Cloud MQTT Callbacks
    # ==========================================
    def on_connect_cloud(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to CLOUD MQTT broker at {self.cloud_host}:{self.cloud_port}")
            # Subscribe to Cloud Advisory channel: ignis/v1/advisory/zone/{zone_id}/command
            advisory_topic = f"ignis/v1/advisory/zone/{self.zone_id}/command"
            self.client_cloud.subscribe(advisory_topic)
            logger.info(f"Subscribed to Cloud advisory topic: {advisory_topic}")
            
            # Sub-Phase D3: Subscribe to lateral coordination topic
            lateral_topic = "ignis/v1/fog/zone/+/lateral"
            self.client_cloud.subscribe(lateral_topic)
            logger.info(f"Subscribed to lateral coordination topic: {lateral_topic}")
        else:
            logger.error(f"Failed to connect to CLOUD MQTT broker, code: {rc}")

    def on_message_cloud(self, client, userdata, msg):
        """Processes incoming messages from the centralized cloud broker."""
        try:
            topic = str(msg.topic) if msg.topic else ""
            payload = json.loads(msg.payload.decode())
            
            # Route by message signature or topic
            if "lateral" in topic or payload.get("message_type") == "lateral_broadcast" or "wind_dir_deg" in payload:
                self._handle_lateral_warning(payload)
            else:
                logger.info(f"Received Cloud Advisory payload: {payload}")
                self._handle_advisory_command(payload)
        except Exception as e:
            logger.error(f"Error handling cloud message: {e}")

    def _handle_advisory_command(self, payload: dict):
        try:
            command_id = payload.get("command_id")
            sequence_number = payload.get("sequence_number", 0)
            timestamp = payload.get("timestamp")
            ttl = payload.get("ttl", 300)
            command = payload.get("command")
            parameters = payload.get("parameters", {})
            issued_by = payload.get("issued_by", "anonymous")
            
            # A. Basic field validation
            if not command_id or not command or not timestamp:
                self.publish_command_response(command_id or "UNKNOWN", "FAILED", "Missing required fields (command_id, command, timestamp)")
                return
                
            # B. Duplicate command prevention
            if command_id in self.processed_command_ids:
                self.publish_command_response(command_id, "FAILED", "Duplicate command ID detected")
                return
                
            # C. Monotonic sequence validation
            if self.last_sequence_number != -1 and sequence_number <= self.last_sequence_number:
                self.publish_command_response(command_id, "FAILED", f"Out of sequence command. Received: {sequence_number}, Last: {self.last_sequence_number}")
                return
                
            # D. Replay protection (TTL check)
            try:
                # Expecting standard ISO format: 2026-07-10T10:25:00Z
                dt = datetime.strptime(timestamp.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                cmd_epoch = calendar.timegm(dt.utctimetuple())
            except Exception as e:
                # Fallback to direct float epoch
                try:
                    cmd_epoch = float(timestamp)
                except Exception:
                    self.publish_command_response(command_id, "FAILED", f"Invalid timestamp format: {timestamp}")
                    return
            
            now_epoch = calendar.timegm(time.gmtime())
            elapsed = now_epoch - cmd_epoch
            if elapsed > ttl or elapsed < -60: # Allow 1 min clock skew
                self.publish_command_response(command_id, "FAILED", f"Command expired. Elapsed time: {elapsed}s, TTL: {ttl}s")
                return
                
            # E. Validate zone ID matches
            target_zone = payload.get("zone_id")
            if target_zone and target_zone != self.zone_id:
                self.publish_command_response(command_id, "FAILED", f"Command intended for zone {target_zone}, not {self.zone_id}")
                return

            # Add to security cache
            self.processed_command_ids.add(command_id)
            if len(self.processed_command_ids) > 1000:
                self.processed_command_ids.remove(next(iter(self.processed_command_ids)))
            self.last_sequence_number = sequence_number
            
            # F. Execute Commands
            success = False
            msg_details = ""
            
            # 1. Manual Overrides
            if command == "set_override_state":
                state = parameters.get("state")
                if state in self.STATE_ORDER:
                    self.override_active = True
                    self.override_state = state
                    self.override_operator = issued_by
                    self.override_reason = f"Manual override to {state} requested by {issued_by}"
                    
                    # Log actions triggered by this override state
                    if state == "ORANGE":
                        self.override_actions = ["activate_mist_perimeter", "notify_control_center"]
                    elif state == "RED":
                        self.override_actions = [
                            "escalate_pre_suppression_to_max",
                            "emergency_alert_control_center",
                            "broadcast_lateral_orange"
                        ]
                    else:
                        self.override_actions = []
                        
                    success = True
                    msg_details = f"State successfully overridden to {state}"
                    logger.info(f"FOG MANUAL STATE OVERRIDE: Clamped to {state}")
                else:
                    msg_details = f"Invalid state value: {state}"
                    
            elif command == "release_override":
                self.override_active = False
                self.override_state = "NONE"
                self.override_operator = "SYSTEM"
                self.override_actions = []
                self.override_reason = "Manual override released"
                success = True
                msg_details = "Manual override released back to dynamic calculation."
                logger.info("FOG MANUAL STATE OVERRIDE: Released")
                
            # 2. Dynamic Threshold Policy Updates
            elif command == "adjust_temperature_threshold":
                val = float(parameters.get("value", 40.0))
                self.fog_processor.sensor_limits["temperature_c"]["confirmation_threshold"] = val
                success = True
                msg_details = f"Temperature confirmation threshold adjusted to {val}°C"
                logger.info(f"POLICY UPDATE: Temperature threshold updated to {val}")
                
            elif command == "adjust_humidity_threshold":
                val = float(parameters.get("value", 25.0))
                self.fog_processor.sensor_limits["humidity_pct"]["confirmation_threshold"] = val
                success = True
                msg_details = f"Humidity confirmation threshold adjusted to {val}%"
                logger.info(f"POLICY UPDATE: Humidity threshold updated to {val}")
                
            elif command == "adjust_gas_threshold":
                val = float(parameters.get("value", 30.0))
                self.fog_processor.sensor_limits["gas_ppm"]["confirmation_threshold"] = val
                success = True
                msg_details = f"Gas confirmation threshold adjusted to {val} PPM"
                logger.info(f"POLICY UPDATE: Gas threshold updated to {val}")
                
            else:
                msg_details = f"Unknown command action: {command}"
                
            # G. Publish Result Response
            if success:
                self.publish_command_response(command_id, "SUCCESS", msg_details)
                # Re-evaluate and publish zone state immediately
                self.evaluate_and_publish_zone_status()
            else:
                self.publish_command_response(command_id, "FAILED", msg_details)
                
        except Exception as e:
            logger.error(f"Error executing cloud advisory command: {e}")

    def _handle_lateral_warning(self, payload: dict):
        try:
            source_zone_id = payload.get("zone_id")
            state = payload.get("state")
            wind_dir_deg = payload.get("wind_dir_deg")
            wind_speed_kmh = payload.get("wind_speed_kmh")
            
            if not source_zone_id or not state:
                logger.warning("Received lateral warning payload missing zone_id or state.")
                return
                
            if source_zone_id == self.zone_id:
                # Ignore own broadcasts
                return
                
            # Find the matching neighbor entry
            neighbor = None
            for n in self.neighbors:
                if n.get("zone_id") == source_zone_id:
                    neighbor = n
                    break
                    
            if not neighbor:
                # Not a neighbor, ignore
                return
                
            # Check wind alignment and source state severity
            aligned = self.check_wind_alignment(
                wind_dir_deg, 
                neighbor.get("bearing_from_neighbor", 0.0), 
                neighbor.get("bearing_tolerance", 45.0)
            )
            
            # Convert states to values for comparison
            state_val = self.STATE_ORDER.get(state, 0)
            yellow_val = self.STATE_ORDER.get("YELLOW", 1)
            
            if aligned and state_val >= yellow_val:
                self.active_lateral_warnings[source_zone_id] = {
                    "zone_id": source_zone_id,
                    "state": state,
                    "timestamp": time.time()
                }
                logger.info(f"Registered lateral warning from neighbor {source_zone_id} | State: {state}")
            else:
                # If not aligned, remove warning if it was previously registered
                if source_zone_id in self.active_lateral_warnings:
                    self.active_lateral_warnings.pop(source_zone_id)
                    logger.info(f"Cleared lateral warning from neighbor {source_zone_id} (wind shifted or state reduced)")
        except Exception as e:
            logger.error(f"Error handling lateral warning: {e}")

    @staticmethod
    def check_wind_alignment(wind_deg: float, target_bearing: float, tolerance: float) -> bool:
        """Returns True if wind_deg is within ±tolerance of target_bearing, handling 360° wrap."""
        diff = abs(wind_deg - target_bearing) % 360
        diff = min(diff, 360 - diff)
        return diff <= tolerance

    @staticmethod
    def compute_vector_wind_average(readings: list) -> tuple:
        """Returns (avg_dir_deg, avg_speed_kmh) using circular vector averaging."""
        import math
        if not readings:
            return (0.0, 0.0)
        sin_sum = sum(math.sin(math.radians(r.get("wind_dir_deg", 0))) for r in readings)
        cos_sum = sum(math.cos(math.radians(r.get("wind_dir_deg", 0))) for r in readings)
        avg_dir = math.degrees(math.atan2(sin_sum / len(readings), cos_sum / len(readings))) % 360
        if avg_dir >= 360.0 - 1e-7:
            avg_dir = 0.0
        avg_speed = sum(r.get("wind_speed_kmh", 0) for r in readings) / len(readings)
        return (avg_dir, avg_speed)

    def _publish_lateral_broadcast(self, zone_state, zone_whi, wind_dir, wind_speed):
        payload = {
            "message_type": "lateral_broadcast",
            "version": "1",
            "zone_id": self.zone_id,
            "state": zone_state,
            "whi": float(zone_whi),
            "wind_dir_deg": float(wind_dir),
            "wind_speed_kmh": float(wind_speed),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        topic = f"ignis/v1/fog/zone/{self.zone_id}/lateral"
        self.client_cloud.publish(topic, json.dumps(payload))
        logger.info(f"Published lateral broadcast: {zone_state} wind={wind_dir:.0f}°")

    def publish_command_response(self, command_id: str, status: str, details: str):
        payload = {
            "message_type": "advisory_response",
            "version": "1",
            "command_id": command_id,
            "zone_id": self.zone_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": status,
            "error_reason": details if status == "FAILED" else "",
            "details": details if status == "SUCCESS" else ""
        }
        response_topic = f"ignis/v1/advisory/zone/{self.zone_id}/response"
        self.client_cloud.publish(response_topic, json.dumps(payload))
        logger.info(f"Published command response to cloud: {status} | {details}")

    # ==========================================
    # Status Aggregation & Heartbeats
    # ==========================================
    def evaluate_and_publish_zone_status(self):
        if not self.node_states:
            return
            
        now = time.time()
        active_records = []
        active_node_ids = []
        
        # Filter timed out nodes (timeout threshold 15s)
        for node_id, record in list(self.node_states.items()):
            try:
                ts_str = record.get("timestamp", "")
                struct_time = time.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
                epoch_ts = calendar.timegm(struct_time)
            except Exception:
                epoch_ts = now
                
            if now - epoch_ts < 15.0 or "timestamp" not in record:
                active_records.append(record)
                active_node_ids.append(node_id)
            else:
                logger.warning(f"Node {node_id} timed out. Removing from active aggregation.")
                self.node_states.pop(node_id, None)

        if not active_records:
            return
            
        # Perform dynamic aggregation calculations
        zone_whi = max(r["whi"] for r in active_records)
        
        # Max state logic
        max_state_val = -1
        zone_state = "GREEN"
        is_clamped = False
        
        for r in active_records:
            s = r["state"]
            val = self.STATE_ORDER.get(s, 0)
            if val > max_state_val:
                max_state_val = val
                zone_state = s
                is_clamped = r.get("is_state_clamped", False)
                
        confirming_sensors = list(set(
            sensor for r in active_records for sensor in r.get("confirming_sensors", [])
        ))
        
        actions_logged = list(set(
            action for r in active_records for action in r.get("actions_logged", [])
        ))
        
        # --- Lateral Pre-emptive Logic ---
        # 1. Expire stale warnings
        if not hasattr(self, "active_lateral_warnings"):
            self.active_lateral_warnings = {}
        if not hasattr(self, "lateral_warning_timeout"):
            self.lateral_warning_timeout = 30
        if not hasattr(self, "lateral_preemptive_active"):
            self.lateral_preemptive_active = False

        now = time.time()
        self.active_lateral_warnings = {
            zid: w for zid, w in self.active_lateral_warnings.items()
            if now - w["timestamp"] < self.lateral_warning_timeout
        }
        
        # 2. Pre-emptive escalation: if any active warnings and we are GREEN
        lateral_sources = []
        if self.active_lateral_warnings and zone_state == "GREEN":
            zone_state = "YELLOW"
            self.lateral_preemptive_active = True
            lateral_sources = list(self.active_lateral_warnings.values())
        else:
            self.lateral_preemptive_active = False

        # APPLY CENTRAL CLOUD ADVISORY OVERRIDES
        if self.override_active:
            zone_state = self.override_state
            is_clamped = True
            actions_logged = self.override_actions
            
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # 1. Publish Zone State Heartbeat (to Local & Cloud)
        state_payload = {
            "message_type": "zone_state",
            "version": "1",
            "zone_id": self.zone_id,
            "timestamp": timestamp,
            "whi": float(zone_whi),
            "state": zone_state,
            "is_state_clamped": bool(is_clamped),
            "confirming_sensors": confirming_sensors,
            "active_nodes": active_node_ids,
            "override_active": self.override_active,
            "preemptive_escalation": self.lateral_preemptive_active,
            "lateral_warning_sources": lateral_sources
        }
        
        state_topic = f"ignis/v1/fog/zone/{self.zone_id}/state"
        self.client_local.publish(state_topic, json.dumps(state_payload))
        self.client_cloud.publish(state_topic, json.dumps(state_payload))
        
        # 2. Trigger Alert on State Transitions
        if zone_state != self.last_zone_state:
            logger.info(f"ZONE {self.zone_id} STATE TRANSITION: {self.last_zone_state} -> {zone_state}")
            
            source_node = "UNKNOWN"
            if not self.override_active:
                for r in active_records:
                    if r["state"] == zone_state:
                        source_node = r["raw_reading"].get("node_id", "UNKNOWN")
                        break
            else:
                source_node = f"CLOUD_ADVISORY_{self.override_operator}"
                
            # Compile Alert Payload
            alert_payload = {
                "message_type": "alert",
                "version": "1",
                "zone_id": self.zone_id,
                "timestamp": timestamp,
                "severity": zone_state,
                "source_node": source_node,
                "whi": float(zone_whi),
                "confirming_sensors": confirming_sensors
            }
            alert_topic = f"ignis/v1/fog/zone/{self.zone_id}/alert"
            self.client_local.publish(alert_topic, json.dumps(alert_payload))
            self.client_cloud.publish(alert_topic, json.dumps(alert_payload))
            
            # Action Logs if ORANGE or RED
            if zone_state in ("ORANGE", "RED"):
                action_payload = {
                    "message_type": "action_log",
                    "version": "1",
                    "zone_id": self.zone_id,
                    "timestamp": timestamp,
                    "actions": actions_logged,
                    "reason": self.override_reason if self.override_active else f"Risk state escalated to {zone_state}"
                }
                action_topic = f"ignis/v1/fog/zone/{self.zone_id}/action_log"
                self.client_local.publish(action_topic, json.dumps(action_payload))
                self.client_cloud.publish(action_topic, json.dumps(action_payload))
                
            # Publish lateral broadcast on state transitions (YELLOW+)
            if self.STATE_ORDER.get(zone_state, 0) >= self.STATE_ORDER["YELLOW"]:
                raw_readings = [r.get("raw_reading", {}) for r in active_records if r.get("raw_reading")]
                wind_dir_avg, wind_speed_avg = self.compute_vector_wind_average(raw_readings)
                self._publish_lateral_broadcast(zone_state, zone_whi, wind_dir_avg, wind_speed_avg)

            self.last_zone_state = zone_state

    def publish_system_heartbeat(self):
        """Sends regular system health metric messages."""
        try:
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            heartbeat = {
                "message_type": "heartbeat",
                "version": "1",
                "zone_id": self.zone_id,
                "timestamp": timestamp,
                "status": "ONLINE",
                "override_active": self.override_active,
                "override_state": self.override_state,
                "sensors_policy": {
                    "temp_c_threshold": self.fog_processor.sensor_limits["temperature_c"]["confirmation_threshold"],
                    "humidity_pct_threshold": self.fog_processor.sensor_limits["humidity_pct"]["confirmation_threshold"],
                    "gas_ppm_threshold": self.fog_processor.sensor_limits["gas_ppm"]["confirmation_threshold"]
                }
            }
            heartbeat_topic = f"ignis/v1/system/fog/zone/{self.zone_id}/heartbeat"
            self.client_local.publish(heartbeat_topic, json.dumps(heartbeat))
            self.client_cloud.publish(heartbeat_topic, json.dumps(heartbeat))
        except Exception as e:
            logger.error(f"Error publishing system heartbeat: {e}")

    def start(self):
        logger.info(f"Starting Fog Node runner for Zone {self.zone_id}")
        
        # Connect to brokers
        logger.info(f"Connecting to LOCAL MQTT Broker at {self.local_host}:{self.local_port}")
        self.client_local.connect(self.local_host, self.local_port, 60)
        
        logger.info(f"Connecting to CLOUD MQTT Broker at {self.cloud_host}:{self.cloud_port}")
        self.client_cloud.connect(self.cloud_host, self.cloud_port, 60)
        
        # Start loops in background
        self.client_local.loop_start()
        self.client_cloud.loop_start()
        
        try:
            while True:
                # Periodic verification, aggregation timeouts check, and heartbeats (every 5 seconds)
                self.evaluate_and_publish_zone_status()
                self.publish_system_heartbeat()
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Interrupt received, stopping...")
        finally:
            self.client_local.loop_stop()
            self.client_cloud.loop_stop()
            self.client_local.disconnect()
            self.client_cloud.disconnect()
            logger.info("Fog Node stopped.")

if __name__ == "__main__":
    runner = FogNodeRunner()
    runner.start()
