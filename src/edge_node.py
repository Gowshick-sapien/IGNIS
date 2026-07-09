class EdgeNode:
    """
    Represents a physical edge sensor cluster node.
    Responsible for packaging raw sensor data into the standardized IGNIS data format.
    """
    def __init__(self, node_id: str, zone_id: str, gps: list):
        self.node_id = node_id
        self.zone_id = zone_id
        self.gps = gps  # [latitude, longitude]

    def format_reading(self, sensor_data: dict, timestamp: str, seasonal_baseline: float = 0.5) -> dict:
        """
        Takes raw sensor readings and standardizes them into the edge telemetry schema.
        
        Args:
            sensor_data (dict): Dictionary containing raw sensor measurements.
            timestamp (str): ISO 8601 formatted timestamp string.
            seasonal_baseline (float): Baseline seasonal risk factor [0.0, 1.0].
            
        Returns:
            dict: Structured telemetry payload.
        """
        payload = {
            "node_id": self.node_id,
            "zone_id": self.zone_id,
            "timestamp": timestamp,
            
            # Environmental parameters
            "temperature_c": float(sensor_data.get("temperature_c", 25.0)),
            "humidity_pct": float(sensor_data.get("humidity_pct", 50.0)),
            "wind_speed_kmh": float(sensor_data.get("wind_speed_kmh", 5.0)),
            "wind_dir_deg": float(sensor_data.get("wind_dir_deg", 0.0)),
            "soil_moisture_pct": float(sensor_data.get("soil_moisture_pct", 30.0)),
            "gas_ppm": float(sensor_data.get("gas_ppm", 15.0)),
            "thermal_anomaly_c": float(sensor_data.get("thermal_anomaly_c", 0.0)),
            
            # Contextual/Metadata parameters
            "light_lux": float(sensor_data.get("light_lux", 1000.0)),
            "rain_mm": float(sensor_data.get("rain_mm", 0.0)),
            "gps": self.gps,
            
            # Helper for decision scoring in Phase A
            "seasonal_baseline": seasonal_baseline
        }
        return payload
