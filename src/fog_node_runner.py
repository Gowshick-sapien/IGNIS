import os
import sys
import json
import time
import logging
import paho.mqtt.client as mqtt

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fog_node import FogNode

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fog_node_runner")

class FogNodeRunner:
    """Manages the Fog Node service daemon, subscribing to edge nodes and publishing zone state."""
    STATE_ORDER = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    
    def __init__(self):
        self.zone_id = os.environ.get("ZONE_ID", "4B")
        self.mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_PORT", 1883))
        
        config_path = os.environ.get("CONFIG_PATH", os.path.join("config", "zone_config.json"))
        self.config = self.load_config(config_path)
        
        # Instantiate the underlying single-node logic processor
        self.fog_processor = FogNode(self.zone_id, self.config)
        
        # In-memory store for the latest decision record of each edge node
        self.node_states = {} # node_id -> decision_record
        
        # Keep track of last published zone state to detect transitions
        self.last_zone_state = "GREEN"
        
        # MQTT Client setup
        self.client = mqtt.Client(client_id=f"fog_node_runner_{self.zone_id}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, 'r') as f:
            return json.load(f)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker successfully.")
            # Subscribe to all edge node readings in this zone
            reading_topic = f"ignis/v1/zone/{self.zone_id}/edge/+/reading"
            self.client.subscribe(reading_topic)
            logger.info(f"Subscribed to readings topic: {reading_topic}")
        else:
            logger.error(f"Failed to connect, return code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            node_id = payload.get("node_id")
            if not node_id:
                logger.warning("Received telemetry payload without node_id.")
                return
                
            # Process single edge node telemetry using FogNode logic
            decision_record = self.fog_processor.process_reading(payload)
            self.node_states[node_id] = decision_record
            
            logger.info(f"Ingested E-Node {node_id} | State: {decision_record['state']} (WHI: {decision_record['whi']:.3f})")
            
            # Re-evaluate and publish aggregated Zone status
            self.evaluate_and_publish_zone_status()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def evaluate_and_publish_zone_status(self):
        if not self.node_states:
            return
            
        # 1. Determine active nodes (nodes reporting in the last 15 seconds)
        now = time.time()
        active_records = []
        active_node_ids = []
        
        # For simplicity in simulation, we treat any node we've ever heard of as active, 
        # unless it hasn't reported for > 15 seconds (resilience check)
        for node_id, record in list(self.node_states.items()):
            # Parse timestamp (e.g. 2026-07-08T09:40:00Z)
            try:
                # Basic timestamp parsing to count elapsed time
                ts_str = record.get("timestamp", "")
                struct_time = time.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
                epoch_ts = time.mktime(struct_time)
                # Note: if simulation uses actual system time UTC, we can check delta.
                # However, in scenario replays time might be manual. Let's rely on standard elapsed checks.
            except Exception:
                epoch_ts = now
                
            # Allow up to 15s timeout
            if now - epoch_ts < 15.0 or "timestamp" not in record:
                active_records.append(record)
                active_node_ids.append(node_id)
            else:
                logger.warning(f"Node {node_id} timed out. Removing from active aggregation.")
                self.node_states.pop(node_id, None)

        if not active_records:
            return
            
        # 2. Perform aggregation
        # Zone WHI = Max of active node WHIs
        zone_whi = max(r["whi"] for r in active_records)
        
        # Zone State = Max State among active nodes
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
                
        # Confirming sensors = Union of confirming sensors
        confirming_sensors = list(set(
            sensor for r in active_records for sensor in r.get("confirming_sensors", [])
        ))
        
        # Actions = Union of actions logged
        actions_logged = list(set(
            action for r in active_records for action in r.get("actions_logged", [])
        ))
        
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # 3. Publish State Heartbeat
        state_payload = {
            "message_type": "zone_state",
            "version": "1",
            "zone_id": self.zone_id,
            "timestamp": timestamp,
            "whi": float(zone_whi),
            "state": zone_state,
            "is_state_clamped": bool(is_clamped),
            "confirming_sensors": confirming_sensors,
            "active_nodes": active_node_ids
        }
        
        state_topic = f"ignis/v1/zone/{self.zone_id}/fog/state"
        self.client.publish(state_topic, json.dumps(state_payload))
        
        # 4. Trigger alert on state escalation or transition
        if zone_state != self.last_zone_state:
            logger.info(f"ZONE {self.zone_id} STATE TRANSITION: {self.last_zone_state} -> {zone_state}")
            
            # Find source node that triggered maximum state
            source_node = "UNKNOWN"
            for r in active_records:
                if r["state"] == zone_state:
                    source_node = r["raw_reading"].get("node_id", "UNKNOWN")
                    break
            
            # Publish Alert Message
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
            alert_topic = f"ignis/v1/zone/{self.zone_id}/fog/alert"
            self.client.publish(alert_topic, json.dumps(alert_payload))
            
            # Publish Action Log if ORANGE or RED
            if zone_state in ("ORANGE", "RED"):
                action_payload = {
                    "message_type": "action_log",
                    "version": "1",
                    "zone_id": self.zone_id,
                    "timestamp": timestamp,
                    "actions": actions_logged,
                    "reason": f"Risk state escalated to {zone_state}"
                }
                action_topic = f"ignis/v1/zone/{self.zone_id}/fog/action_log"
                self.client.publish(action_topic, json.dumps(action_payload))
                
            self.last_zone_state = zone_state

    def start(self):
        logger.info(f"Starting Fog Node runner for Zone {self.zone_id}")
        logger.info(f"Connecting to MQTT Broker at {self.mqtt_host}:{self.mqtt_port}")
        
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        
        # Start a loop in background
        self.client.loop_start()
        
        try:
            while True:
                # Periodic verification / heartbeat (e.g. check for timeouts)
                self.evaluate_and_publish_zone_status()
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Interrupt received, stopping...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Fog Node stopped.")

if __name__ == "__main__":
    runner = FogNodeRunner()
    runner.start()
