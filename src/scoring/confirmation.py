def evaluate_confirmations(reading: dict, sensor_limits: dict) -> tuple:
    """
    Evaluates which raw sensor readings have crossed their respective confirmation thresholds.
    Returns:
        tuple: (list of confirming sensor keys, integer confirmation count)
    """
    confirming_sensors = []
    
    # 1. Temperature (>= threshold)
    t_cfg = sensor_limits.get("temperature_c", {})
    if "confirmation_threshold" in t_cfg:
        if reading.get("temperature_c", 0.0) >= t_cfg["confirmation_threshold"]:
            confirming_sensors.append("temperature_c")
            
    # 2. Humidity (<= threshold)
    h_cfg = sensor_limits.get("humidity_pct", {})
    if "confirmation_threshold" in h_cfg:
        if reading.get("humidity_pct", 100.0) <= h_cfg["confirmation_threshold"]:
            confirming_sensors.append("humidity_pct")
            
    # 3. Wind Speed (>= threshold)
    w_cfg = sensor_limits.get("wind_speed_kmh", {})
    if "confirmation_threshold" in w_cfg:
        if reading.get("wind_speed_kmh", 0.0) >= w_cfg["confirmation_threshold"]:
            confirming_sensors.append("wind_speed_kmh")
            
    # 4. Soil Moisture (<= threshold)
    sm_cfg = sensor_limits.get("soil_moisture_pct", {})
    if "confirmation_threshold" in sm_cfg:
        if reading.get("soil_moisture_pct", 100.0) <= sm_cfg["confirmation_threshold"]:
            confirming_sensors.append("soil_moisture_pct")
            
    # 5. Gas Level (>= threshold)
    g_cfg = sensor_limits.get("gas_ppm", {})
    if "confirmation_threshold" in g_cfg:
        if reading.get("gas_ppm", 0.0) >= g_cfg["confirmation_threshold"]:
            confirming_sensors.append("gas_ppm")
            
    # 6. Thermal Anomaly (>= threshold)
    ta_cfg = sensor_limits.get("thermal_anomaly_c", {})
    if "confirmation_threshold" in ta_cfg:
        if reading.get("thermal_anomaly_c", 0.0) >= ta_cfg["confirmation_threshold"]:
            confirming_sensors.append("thermal_anomaly_c")
            
    return confirming_sensors, len(confirming_sensors)
