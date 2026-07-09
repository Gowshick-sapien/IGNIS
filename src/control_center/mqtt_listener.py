import json
import logging
import threading
import time
from collections import deque
import paho.mqtt.client as mqtt

logger = logging.getLogger("mqtt_listener")

class MQTTListener:
    """Listens to versioned IGNIS topics on MQTT broker and caches updates for web consumers."""
    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        
        # In-memory system state caches
        self.zone_states = {}       # zone_id -> last zone state dict
        self.edge_readings = {}     # node_id -> last telemetry dict
        self.event_log = deque(maxlen=100) # Deque of historical alerts and action logs
        
        # Thread-safety lock for state caches
        self.lock = threading.Lock()
        
        # List of registered async/thread-safe client queues for SSE
        self.sse_queues = []
        self.sse_queues_lock = threading.Lock()
        
        # MQTT Client setup
        self.client = mqtt.Client(client_id="ignis_control_center_listener")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Control Center MQTT Listener connected.")
            # Subscribe to versioned topics
            topics = [
                ("ignis/v1/zone/+/edge/+/reading", 0),
                ("ignis/v1/zone/+/fog/state", 0),
                ("ignis/v1/zone/+/fog/alert", 0),
                ("ignis/v1/zone/+/fog/action_log", 0)
            ]
            self.client.subscribe(topics)
            logger.info("Subscribed to all telemetry, state, alert, and log topics.")
        else:
            logger.error(f"Control Center listener failed to connect, code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Extract topic attributes
            parts = topic.split('/')
            
            with self.lock:
                if "reading" in topic:
                    # ignis/v1/zone/{zone_id}/edge/{node_id}/reading
                    zone_id = parts[3]
                    node_id = parts[5]
                    # Update local cache
                    self.edge_readings[node_id] = payload
                    
                elif "state" in topic:
                    # ignis/v1/zone/{zone_id}/fog/state
                    zone_id = parts[3]
                    self.zone_states[zone_id] = payload
                    
                elif "alert" in topic or "action_log" in topic:
                    # Logs and alerts go to the scrollable event log
                    payload["topic"] = topic
                    payload["local_time"] = time.strftime("%H:%M:%S")
                    self.event_log.appendleft(payload)
            
            # Broadcast to SSE client queues
            self.broadcast_to_sse({
                "topic": topic,
                "data": payload
            })
            
        except Exception as e:
            logger.error(f"Error parsing MQTT message on {msg.topic}: {e}")

    def register_sse_queue(self, queue):
        with self.sse_queues_lock:
            self.sse_queues.append(queue)
            logger.info(f"Registered new SSE client queue. Active clients: {len(self.sse_queues)}")

    def unregister_sse_queue(self, queue):
        with self.sse_queues_lock:
            if queue in self.sse_queues:
                self.sse_queues.remove(queue)
                logger.info(f"Unregistered SSE client queue. Active clients: {len(self.sse_queues)}")

    def broadcast_to_sse(self, message: dict):
        # We need to dispatch to registered clients
        with self.sse_queues_lock:
            for q in self.sse_queues:
                try:
                    # Put message in queue (which could be an asyncio loop queue or synchronous thread queue)
                    q.put_nowait(message)
                except Exception as e:
                    # Queue might be full or closed
                    pass

    def get_snapshot(self) -> dict:
        """Returns a snapshot of the current states for initial page loads."""
        with self.lock:
            return {
                "zone_states": list(self.zone_states.values()),
                "edge_readings": list(self.edge_readings.values()),
                "event_log": list(self.event_log)
            }

    def start(self):
        logger.info(f"Starting MQTT Listener thread connecting to {self.mqtt_host}:{self.mqtt_port}")
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT Listener thread stopped.")
