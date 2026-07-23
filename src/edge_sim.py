import os
import sys
import json
import time
import random
import logging
from abc import ABC, abstractmethod
# pyrefly: ignore [missing-import]
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("edge_sim")

class TelemetryProvider(ABC):
    """Abstract base class for providing sensor readings."""
    @abstractmethod
    def get_reading(self) -> dict:
        """Returns a dictionary of raw sensor values."""
        pass

class RandomWalkProvider(TelemetryProvider):
    """Generates sensor data that drifts randomly within normal limits."""
    def __init__(self):
        # Initial baseline states
        self.default_state = {
            "temperature_c": 28.0,
            "humidity_pct": 55.0,
            "wind_speed_kmh": 6.0,
            "wind_dir_deg": 180.0,
            "soil_moisture_pct": 28.0,
            "gas_ppm": 12.0,
            "thermal_anomaly_c": 0.2,
            "light_lux": 20000.0,
            "rain_mm": 0.0
        }
        self.state = self.default_state.copy()
        # Hard limits to clamp the drift within baseline ranges
        self.limits = {
            "temperature_c": (20.0, 35.0),
            "humidity_pct": (35.0, 70.0),
            "wind_speed_kmh": (2.0, 15.0),
            "wind_dir_deg": (0.0, 360.0),
            "soil_moisture_pct": (20.0, 35.0),
            "gas_ppm": (8.0, 20.0),
            "thermal_anomaly_c": (0.0, 1.0),
            "light_lux": (5000.0, 60000.0),
            "rain_mm": (0.0, 5.0)
        }

    def reset(self):
        self.state = self.default_state.copy()

    def get_reading(self) -> dict:
        # Apply small random walks to each parameter
        for param, val in self.state.items():
            if param == "wind_dir_deg":
                drift = random.uniform(-10.0, 10.0)
            elif param == "light_lux":
                drift = random.uniform(-1000.0, 1000.0)
            elif param == "rain_mm":
                drift = random.uniform(-0.1, 0.1) if random.random() > 0.8 else 0.0
            else:
                drift = random.uniform(-0.3, 0.3)
            
            new_val = val + drift
            
            # Clamp to limits
            min_v, max_v = self.limits[param]
            self.state[param] = max(min_v, min(max_v, new_val))
            
        return self.state.copy()

class ScenarioProvider(TelemetryProvider):
    """Returns fixed injected scenario readings."""
    def __init__(self, fallback_provider: TelemetryProvider):
        self.fallback = fallback_provider
        self.current_reading = None

    def set_reading(self, data: dict):
        self.current_reading = data

    def get_reading(self) -> dict:
        if self.current_reading:
            # Emit the injected scenario reading
            return self.current_reading.copy()
        return self.fallback.get_reading()

class FaultInjectionProvider(TelemetryProvider):
    """Simulates a sensor fault by injecting stuck/corrupt values on specific parameters."""
    def __init__(self, base_provider: TelemetryProvider, fault_sensor: str, fault_value: float):
        self.base = base_provider
        self.fault_sensor = fault_sensor
        self.fault_value = fault_value

    def get_reading(self) -> dict:
        data = self.base.get_reading()
        if self.fault_sensor in data:
            data[self.fault_sensor] = self.fault_value
        return data

class EdgeNodeSimulator:
    """Manages the lifecycle of an Edge Node simulation process."""
    def __init__(self):
        self.node_id = os.environ.get("NODE_ID", "E11")
        self.zone_id = os.environ.get("ZONE_ID", "4B")
        self.mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_PORT", 1883))
        
        gps_lat = float(os.environ.get("GPS_LAT", 21.94))
        gps_lon = float(os.environ.get("GPS_LON", 86.32))
        self.gps = [gps_lat, gps_lon]
        
        self.tick_interval = float(os.environ.get("TICK_INTERVAL", 3.0))
        self.seasonal_baseline = float(os.environ.get("SEASONAL_BASELINE", 0.5))
        
        # Telemetry Providers
        self.baseline_provider = RandomWalkProvider()
        self.scenario_provider = ScenarioProvider(self.baseline_provider)
        self.active_provider = self.baseline_provider
        
        self.sequence_number = 0
        self.running = False
        
        import threading
        self.tick_event = threading.Event()
        
        # MQTT Client setup
        self.client = mqtt.Client(client_id=f"edge_sim_{self.zone_id}_{self.node_id}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker successfully.")
            # Subscribe to control topic
            control_topic = f"ignis/v1/system/zone/{self.zone_id}/edge/{self.node_id}/control"
            self.client.subscribe(control_topic)
            logger.info(f"Subscribed to control topic: {control_topic}")
        else:
            logger.error(f"Failed to connect, return code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received control command on {msg.topic}: {payload}")
            
            message_type = payload.get("message_type")
            if message_type != "control":
                logger.warning(f"Ignored unexpected message type: {message_type}")
                return
                
            if "seed" in payload:
                seed_val = payload["seed"]
                random.seed(seed_val)
                self.baseline_provider.reset()
                logger.info(f"Seeded random generator with: {seed_val} and reset baseline provider state")
                
            command = payload.get("command")
            if command == "set_mode":
                mode = payload.get("mode", "baseline")
                if mode == "baseline":
                    self.active_provider = self.baseline_provider
                    logger.info("Switched to Baseline data generation mode.")
                elif mode == "scenario":
                    sensor_data = payload.get("sensor_data", {})
                    if "seasonal_baseline" in payload:
                        self.seasonal_baseline = payload["seasonal_baseline"]
                    self.scenario_provider.set_reading(sensor_data)
                    self.active_provider = self.scenario_provider
                    logger.info(f"Switched to Scenario mode with seasonal_baseline={self.seasonal_baseline}")
                elif mode == "fault":
                    fault_sensor = payload.get("fault_sensor")
                    fault_value = float(payload.get("fault_value", 0.0))
                    # Layer fault on top of baseline
                    self.active_provider = FaultInjectionProvider(
                        self.baseline_provider, fault_sensor, fault_value
                    )
                    logger.info(f"Switched to Fault mode. Forcing {fault_sensor} = {fault_value}")
            else:
                logger.warning(f"Unknown control command: {command}")
            
            # Wake up the sleep loop immediately
            self.tick_event.set()
        except Exception as e:
            logger.error(f"Error handling control message: {e}")

    def start(self):
        logger.info(f"Starting Edge Simulator {self.node_id} (Zone {self.zone_id})")
        logger.info(f"Connecting to MQTT Broker {self.mqtt_host}:{self.mqtt_port}")
        
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
        
        self.running = True
        reading_topic = f"ignis/v1/telemetry/zone/{self.zone_id}/edge/{self.node_id}"
        
        try:
            while self.running:
                # Clear the event before running the tick
                self.tick_event.clear()
                
                # 1. Fetch telemetry values
                sensor_values = self.active_provider.get_reading()
                
                # 2. Package telemetry
                self.sequence_number += 1
                telemetry = {
                    "message_type": "reading",
                    "version": "1",
                    "node_id": self.node_id,
                    "zone_id": self.zone_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "sequence": self.sequence_number,
                    "temperature_c": float(sensor_values.get("temperature_c")),
                    "humidity_pct": float(sensor_values.get("humidity_pct")),
                    "wind_speed_kmh": float(sensor_values.get("wind_speed_kmh")),
                    "wind_dir_deg": float(sensor_values.get("wind_dir_deg")),
                    "soil_moisture_pct": float(sensor_values.get("soil_moisture_pct")),
                    "gas_ppm": float(sensor_values.get("gas_ppm")),
                    "thermal_anomaly_c": float(sensor_values.get("thermal_anomaly_c")),
                    "light_lux": float(sensor_values.get("light_lux")),
                    "rain_mm": float(sensor_values.get("rain_mm")),
                    "gps": self.gps,
                    "seasonal_baseline": self.seasonal_baseline
                }
                
                # 3. Publish to MQTT
                logger.info(f"Publishing sequence {self.sequence_number} | State Mode: {self.active_provider.__class__.__name__}")
                self.client.publish(reading_topic, json.dumps(telemetry))
                
                # 4. Wait for next tick, interruptible by control commands
                self.tick_event.wait(self.tick_interval)
                
        except KeyboardInterrupt:
            logger.info("Interrupt received, stopping...")
        finally:
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Edge Simulator stopped.")

if __name__ == "__main__":
    simulator = EdgeNodeSimulator()
    simulator.start()
