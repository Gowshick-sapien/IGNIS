def normalize_value(val: float, val_min: float, val_max: float, invert: bool = False) -> float:
    """
    Helper function to scale a raw value to a [0.0, 1.0] range.
    If invert is True, a lower raw value yields a higher normalized score.
    """
    if val_max == val_min:
        return 0.0
    
    # Clamp value within [min, max]
    clamped = max(val_min, min(val_max, val))
    
    normalized = (clamped - val_min) / (val_max - val_min)
    if invert:
        normalized = 1.0 - normalized
        
    return normalized

def normalize_time_of_day(hour: int) -> float:
    """
    Normalizes time of day to [0.0, 1.0], peaking at 14:00 (2 PM).
    """
    # Peak is 14:00. At 2:00 AM (12 hours away), risk is minimum (0.0)
    hour_clamped = max(0, min(23, hour))
    difference = abs(hour_clamped - 14)
    normalized = 1.0 - (difference / 12.0)
    return max(0.0, min(1.0, normalized))

def normalize_reading(reading: dict, sensor_limits: dict) -> dict:
    """
    Takes a raw reading dict and limits dict, returning a dictionary of normalized values [0.0, 1.0].
    """
    normalized = {}
    
    # 1. Temperature (higher is higher risk)
    t_limits = sensor_limits["temperature_c"]
    normalized["temperature_c"] = normalize_value(
        reading.get("temperature_c", 0.0),
        t_limits["min"],
        t_limits["max"],
        invert=False
    )
    
    # 2. Humidity (lower is higher risk)
    h_limits = sensor_limits["humidity_pct"]
    normalized["humidity_pct"] = normalize_value(
        reading.get("humidity_pct", 100.0),
        h_limits["min"],
        h_limits["max"],
        invert=True
    )
    
    # 3. Wind Speed (higher is higher risk)
    w_limits = sensor_limits["wind_speed_kmh"]
    normalized["wind_speed_kmh"] = normalize_value(
        reading.get("wind_speed_kmh", 0.0),
        w_limits["min"],
        w_limits["max"],
        invert=False
    )
    
    # 4. Soil Moisture (lower is higher risk)
    sm_limits = sensor_limits["soil_moisture_pct"]
    normalized["soil_moisture_pct"] = normalize_value(
        reading.get("soil_moisture_pct", 100.0),
        sm_limits["min"],
        sm_limits["max"],
        invert=True
    )
    
    # 5. Gas Level (higher is higher risk)
    g_limits = sensor_limits["gas_ppm"]
    normalized["gas_ppm"] = normalize_value(
        reading.get("gas_ppm", 0.0),
        g_limits["min"],
        g_limits["max"],
        invert=False
    )
    
    # 6. Thermal Anomaly (higher is higher risk)
    ta_limits = sensor_limits["thermal_anomaly_c"]
    normalized["thermal_anomaly_c"] = normalize_value(
        reading.get("thermal_anomaly_c", 0.0),
        ta_limits["min"],
        ta_limits["max"],
        invert=False
    )
    
    # 7. Time of Day
    # Extract hour from timestamp (iso format, e.g. "2026-07-06T14:30:00")
    timestamp_str = reading.get("timestamp", "")
    hour = 12  # default if parse fails
    try:
        # Simple extraction for ISO strings like "2026-07-06T14:30:00"
        if "T" in timestamp_str:
            time_part = timestamp_str.split("T")[1]
            hour = int(time_part.split(":")[0])
    except (IndexError, ValueError):
        pass
    normalized["time_of_day"] = normalize_time_of_day(hour)
    
    # 8. Seasonal Baseline
    # This comes as a direct factor from reading/metadata or scenario
    normalized["seasonal_baseline"] = float(reading.get("seasonal_baseline", 0.5))
    
    return normalized
