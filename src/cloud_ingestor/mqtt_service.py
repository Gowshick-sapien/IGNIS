import os
import json
import time
import calendar
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

logger = logging.getLogger("cloud_ingestor_mqtt")

class CloudMQTTService:
    """Subscribes to all central cloud topics, computes performance metrics, and logs them to database."""
    def __init__(self, db_wrapper):
        self.db = db_wrapper
        self.mqtt_host = os.environ.get("CLOUD_MQTT_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("CLOUD_MQTT_PORT", 1884))
        
        self.client = mqtt.Client(client_id="ignis_cloud_ingestor")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Offline write buffer: list of tuples (measurement, tags, fields, timestamp)
        self.offline_buffer = []
        self.max_buffer_size = 5000
        
        # InfluxDB online/offline cache state to avoid blocking the MQTT thread
        self.db_online = True
        self.last_db_check_time = 0
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to central Cloud Broker successfully.")
            # Publish ingestor status to central system
            self.publish_health_status("ONLINE")
            
            # Subscribe to all ignis/v1 topics
            self.client.subscribe("ignis/v1/#")
            logger.info("Subscribed to ignis/v1/#")
        else:
            logger.error(f"Cloud Broker connection failed, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from Cloud Broker. Return code: {rc}")

    def publish_health_status(self, status: str):
        """Publishes health heartbeats for the ingestor service itself."""
        try:
            payload = {
                "message_type": "ingestor_heartbeat",
                "version": "1",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": status
            }
            self.client.publish("ignis/v1/system/cloud/ingestor/heartbeat", json.dumps(payload), retain=True)
        except Exception as e:
            logger.error(f"Error publishing ingestor health status: {e}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # 1. Parse topic
            parts = topic.split('/')
            if len(parts) < 3:
                return
                
            now_epoch = calendar.timegm(time.gmtime())
            
            # 2. Match topics and extract fields
            if "telemetry" in topic:
                # ignis/v1/telemetry/zone/{zone_id}/edge/{node_id}
                zone_id = parts[4]
                node_id = parts[6]
                self.process_telemetry(payload, zone_id, node_id, now_epoch)
                
            elif "state" in topic:
                # ignis/v1/fog/zone/{zone_id}/state
                zone_id = parts[4]
                self.process_zone_state(payload, zone_id, now_epoch)
                
            elif "alert" in topic:
                # ignis/v1/fog/zone/{zone_id}/alert
                zone_id = parts[4]
                self.process_alert(payload, zone_id)
                
            elif "action_log" in topic:
                # ignis/v1/fog/zone/{zone_id}/action_log
                zone_id = parts[4]
                self.process_action_log(payload, zone_id)
                
            elif "lateral" in topic:
                # ignis/v1/fog/zone/{zone_id}/lateral
                zone_id = parts[4]
                self.process_lateral_event(payload, zone_id)
                
            elif "response" in topic:
                # ignis/v1/advisory/zone/{zone_id}/response
                zone_id = parts[4]
                self.process_advisory_response(payload, zone_id)
                
            elif "heartbeat" in topic:
                # ignis/v1/system/fog/zone/{zone_id}/heartbeat
                if "fog" in topic:
                    zone_id = parts[5]
                    self.process_fog_heartbeat(payload, zone_id)
                    
        except Exception as e:
            logger.error(f"Error handling message on {msg.topic}: {e}")

    # ==========================================
    # Parsing and Ingestion Processors
    # ==========================================
    def process_telemetry(self, payload: dict, zone_id: str, node_id: str, now_epoch: float):
        ts_str = payload.get("timestamp")
        
        # Calculate Latencies
        fog_to_cloud_latency = 0.0
        try:
            dt = datetime.strptime(ts_str.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
            cmd_epoch = calendar.timegm(dt.utctimetuple())
            fog_to_cloud_latency = max(0.0, now_epoch - cmd_epoch)
        except Exception as e:
            logger.warning(f"Error calculating fog-to-cloud latency: {e}")
            cmd_epoch = now_epoch
            
        # Ingestion Latency
        cloud_ingestion_latency = max(0.0, time.time() - now_epoch)
        
        tags = {"zone_id": zone_id, "node_id": node_id}
        fields = {
            "temperature_c": float(payload.get("temperature_c", 0.0)),
            "humidity_pct": float(payload.get("humidity_pct", 0.0)),
            "wind_speed_kmh": float(payload.get("wind_speed_kmh", 0.0)),
            "wind_dir_deg": float(payload.get("wind_dir_deg", 0.0)),
            "soil_moisture_pct": float(payload.get("soil_moisture_pct", 0.0)),
            "gas_ppm": float(payload.get("gas_ppm", 0.0)),
            "thermal_anomaly_c": float(payload.get("thermal_anomaly_c", 0.0)),
            "light_lux": float(payload.get("light_lux", 0.0)),
            "rain_mm": float(payload.get("rain_mm", 0.0)),
            "sequence": int(payload.get("sequence", 0))
        }
        
        # Write Telemetry Record
        write_start = time.time()
        self.safe_write("telemetry", tags, fields, ts_str)
        write_end = time.time()
        
        # Write Latency metrics
        influx_write_latency = write_end - write_start
        cloud_end_to_end_latency = fog_to_cloud_latency + cloud_ingestion_latency + influx_write_latency
        
        latency_tags = {"zone_id": zone_id, "node_id": node_id, "metric_type": "telemetry"}
        latency_fields = {
            "fog_to_cloud_latency": float(fog_to_cloud_latency),
            "cloud_ingestion_latency": float(cloud_ingestion_latency),
            "influx_write_latency": float(influx_write_latency),
            "cloud_end_to_end_latency": float(cloud_end_to_end_latency)
        }
        self.safe_write("performance_metrics", latency_tags, latency_fields, ts_str)

    def process_zone_state(self, payload: dict, zone_id: str, now_epoch: float):
        ts_str = payload.get("timestamp")
        tags = {"zone_id": zone_id}
        fields = {
            "whi": float(payload.get("whi", 0.0)),
            "state": str(payload.get("state", "GREEN")),
            "is_state_clamped": bool(payload.get("is_state_clamped", False)),
            "override_active": bool(payload.get("override_active", False))
        }
        self.safe_write("zone_state", tags, fields, ts_str)
        
        # Log system health as ONLINE
        health_fields = {"status": "ONLINE", "details": f"State reported: {fields['state']}"}
        self.safe_write("system_health", {"component": f"fog_node_{zone_id}"}, health_fields, ts_str)

    def process_alert(self, payload: dict, zone_id: str):
        ts_str = payload.get("timestamp")
        tags = {"zone_id": zone_id, "source_node": str(payload.get("source_node", "UNKNOWN"))}
        fields = {
            "severity": str(payload.get("severity", "GREEN")),
            "whi": float(payload.get("whi", 0.0))
        }
        self.safe_write("alerts", tags, fields, ts_str)

    def process_action_log(self, payload: dict, zone_id: str):
        ts_str = payload.get("timestamp")
        tags = {"zone_id": zone_id}
        # Serialize list of actions to a JSON string
        actions = payload.get("actions", [])
        fields = {
            "actions": json.dumps(actions),
            "reason": str(payload.get("reason", ""))
        }
        self.safe_write("action_logs", tags, fields, ts_str)

    def process_lateral_event(self, payload: dict, zone_id: str):
        ts_str = payload.get("timestamp")
        tags = {"zone_id": zone_id}
        fields = {
            "state": str(payload.get("state", "GREEN")),
            "wind_dir_deg": float(payload.get("wind_dir_deg", 0.0)),
            "wind_speed_kmh": float(payload.get("wind_speed_kmh", 0.0)),
            "whi": float(payload.get("whi", 0.0))
        }
        self.safe_write("lateral_events", tags, fields, ts_str)

    def process_advisory_response(self, payload: dict, zone_id: str):
        ts_str = payload.get("timestamp")
        tags = {
            "zone_id": zone_id, 
            "command_id": str(payload.get("command_id", "UNKNOWN"))
        }
        fields = {
            "status": str(payload.get("status", "SUCCESS")),
            "error_reason": str(payload.get("error_reason", "")),
            "details": str(payload.get("details", ""))
        }
        self.safe_write("audit_logs", tags, fields, ts_str)

    def process_fog_heartbeat(self, payload: dict, zone_id: str):
        ts_str = payload.get("timestamp")
        tags = {"component": f"fog_node_{zone_id}"}
        fields = {
            "status": str(payload.get("status", "ONLINE")),
            "override_active": bool(payload.get("override_active", False)),
            "details": json.dumps(payload.get("sensors_policy", {}))
        }
        self.safe_write("system_health", tags, fields, ts_str)

    # ==========================================
    # Buffer and Flush Logic
    # ==========================================
    def safe_write(self, measurement: str, tags: dict, fields: dict, timestamp: str = None):
        """Performs a write, buffering if InfluxDB is offline."""
        current_time = time.time()
        
        # If DB is marked offline, check if we should retry connecting/pinging
        if not self.db_online:
            # 10 second cooldown period to prevent blocking the MQTT thread
            if current_time - self.last_db_check_time < 10:
                self._buffer_record(measurement, tags, fields, timestamp)
                return
                
        try:
            # Check if database is offline or write API fails (only ping if we were offline)
            if not self.db_online:
                if not self.db.ping():
                    raise ConnectionError("InfluxDB ping failed.")
                self.db_online = True
                logger.info("InfluxDB connection restored on MQTT service.")
                
            # Perform any buffered flushes first
            if self.offline_buffer:
                self.flush_buffer()
            
            # Write current record
            self.db.write_record(measurement, tags, fields, timestamp)
            self.db_online = True
        except Exception as e:
            logger.warning(f"InfluxDB write failed. Buffering record. Error: {e}")
            self.db_online = False
            self.last_db_check_time = current_time
            self._buffer_record(measurement, tags, fields, timestamp)

    def _buffer_record(self, measurement: str, tags: dict, fields: dict, timestamp: str):
        if len(self.offline_buffer) < self.max_buffer_size:
            self.offline_buffer.append((measurement, tags, fields, timestamp))
        else:
            logger.error("Database offline buffer full! Dropping oldest record.")
            self.offline_buffer.pop(0)
            self.offline_buffer.append((measurement, tags, fields, timestamp))

    def flush_buffer(self):
        """Flushes the buffered items when database returns online."""
        if not self.offline_buffer:
            return
            
        logger.info(f"InfluxDB is back online. Flushing {len(self.offline_buffer)} buffered records.")
        flushed_count = 0
        try:
            while self.offline_buffer:
                measurement, tags, fields, timestamp = self.offline_buffer[0]
                self.db.write_record(measurement, tags, fields, timestamp)
                self.offline_buffer.pop(0)
                flushed_count += 1
            logger.info(f"Successfully flushed {flushed_count} records.")
            self.db_online = True
        except Exception as e:
            self.db_online = False
            self.last_db_check_time = time.time()
            logger.warning(f"Flush interrupted, InfluxDB went offline again. Buffered remaining: {len(self.offline_buffer)}. Error: {e}")
            raise e

    # ==========================================
    # Service Lifecycle
    # ==========================================
    def start(self):
        logger.info(f"Connecting to Cloud MQTT Broker at {self.mqtt_host}:{self.mqtt_port}")
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()

    def stop(self):
        self.publish_health_status("OFFLINE")
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Cloud MQTT Service stopped.")

import os
