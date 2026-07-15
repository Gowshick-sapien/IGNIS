class ScenarioGenerator:
    """
    Generates structured lists of raw sensor values representing test scenarios.
    These values can be fed to EdgeNode.format_reading() to generate standard telemetry payloads.
    """
    
    @staticmethod
    def get_normal_day_scenario(steps: int = 6) -> list:
        """
        Scenario S1: Normal Day.
        Slow natural drift within normal bounds. Everything stays GREEN.
        """
        scenario = []
        base_temp = 28.0
        base_hum = 55.0
        base_wind = 6.0
        base_sm = 28.0
        base_gas = 12.0
        base_ta = 0.2
        
        for i in range(steps):
            hour = 8 + i
            timestamp = f"2026-07-06T{hour:02d}:00:00"
            
            # Gentle drift
            sensor_data = {
                "temperature_c": base_temp + (i * 0.4),
                "humidity_pct": base_hum - (i * 0.5),
                "wind_speed_kmh": base_wind + (i * 0.3),
                "wind_dir_deg": 180 + (i * 5),
                "soil_moisture_pct": base_sm - (i * 0.2),
                "gas_ppm": base_gas + (i * 0.1),
                "thermal_anomaly_c": base_ta + (i * 0.05),
                "light_lux": 20000 + (10000 * (i if i < 4 else 8 - i)),
                "rain_mm": 0.0
            }
            scenario.append({
                "timestamp": timestamp,
                "sensor_data": sensor_data,
                "seasonal_baseline": 0.3  # Moderate risk season
            })
        return scenario

    @staticmethod
    def get_slow_building_risk_scenario(steps: int = 6) -> list:
        """
        Scenario S2: Slow-Building Risk.
        Environmental parameters drift towards dangerous levels over hours.
        WHI rises and crosses YELLOW, but doesn't reach ORANGE/RED yet.
        """
        scenario = []
        for i in range(steps):
            hour = 9 + i
            timestamp = f"2026-07-06T{hour:02d}:00:00"
            
            # Rising temperature, dropping soil moisture and humidity, rising wind
            sensor_data = {
                "temperature_c": 30.0 + (i * 2.1),      # 30.0 -> 40.5
                "humidity_pct": 45.0 - (i * 4.6),       # 45.0 -> 22.0
                "wind_speed_kmh": 8.0 + (i * 2.0),       # 8.0 -> 18.0
                "wind_dir_deg": 210 + (i * 2),
                "soil_moisture_pct": 26.0 - (i * 2.7),   # 26.0 -> 12.5
                "gas_ppm": 14.0 + (i * 0.5),            # Stays low: 14 -> 16.5
                "thermal_anomaly_c": 0.5 + (i * 0.2),    # Stays low: 0.5 -> 1.5
                "light_lux": 45000 + (i * 1000),
                "rain_mm": 0.0
            }
            scenario.append({
                "timestamp": timestamp,
                "sensor_data": sensor_data,
                "seasonal_baseline": 0.8  # Dry summer baseline
            })
        return scenario

    @staticmethod
    def get_sudden_ignition_scenario(steps: int = 6) -> list:
        """
        Scenario S3: Sudden Ignition.
        Starts normal, then a sudden fire breaks out (multiple sensor spikes).
        Should successfully escalate to ORANGE and RED.
        """
        scenario = []
        for i in range(steps):
            hour = 12 + i
            timestamp = f"2026-07-06T{hour:02d}:00:00"
            
            # Steps 0 and 1 are normal
            if i < 2:
                sensor_data = {
                    "temperature_c": 32.0,
                    "humidity_pct": 40.0,
                    "wind_speed_kmh": 10.0,
                    "wind_dir_deg": 220,
                    "soil_moisture_pct": 20.0,
                    "gas_ppm": 12.0,
                    "thermal_anomaly_c": 0.2,
                    "light_lux": 50000,
                    "rain_mm": 0.0
                }
            # Step 2: Smoldering/Early Ignition
            elif i == 2:
                sensor_data = {
                    "temperature_c": 35.5,
                    "humidity_pct": 32.0,
                    "wind_speed_kmh": 12.0,
                    "wind_dir_deg": 220,
                    "soil_moisture_pct": 18.0,
                    "gas_ppm": 28.0,                  # Slight gas increase
                    "thermal_anomaly_c": 1.5,         # Thermal anomaly detectable
                    "light_lux": 48000,
                    "rain_mm": 0.0
                }
            # Step 3: Flame/Ignition confirmed
            elif i == 3:
                sensor_data = {
                    "temperature_c": 41.0,           # Exceeds confirmation threshold (40)
                    "humidity_pct": 22.0,            # Exceeds confirmation threshold (25)
                    "wind_speed_kmh": 15.0,
                    "wind_dir_deg": 230,
                    "soil_moisture_pct": 12.0,
                    "gas_ppm": 45.0,                  # Exceeds confirmation threshold (30)
                    "thermal_anomaly_c": 3.8,         # Exceeds confirmation threshold (3.0)
                    "light_lux": 42000,
                    "rain_mm": 0.0
                }
            # Step 4: Rapid propagation
            else:
                sensor_data = {
                    "temperature_c": 49.0,           # High temp
                    "humidity_pct": 12.0,            # Bone dry
                    "wind_speed_kmh": 22.0,           # High wind
                    "wind_dir_deg": 240,
                    "soil_moisture_pct": 6.0,            # Critically low soil moisture
                    "gas_ppm": 85.0,                  # High gas
                    "thermal_anomaly_c": 7.5,         # High thermal anomaly
                    "light_lux": 35000,
                    "rain_mm": 0.0
                }
                
            scenario.append({
                "timestamp": timestamp,
                "sensor_data": sensor_data,
                "seasonal_baseline": 0.85  # Peak dry summer baseline
            })
        return scenario

    @staticmethod
    def get_single_sensor_fault_scenario(steps: int = 6) -> list:
        """
        Scenario S4: Single Sensor Fault.
        Starts as a hot, dry day (moderate risk). Then the gas sensor spikes due to failure.
        The WHI rises past the ORANGE threshold (> 0.60), but the state machine clamps
        it to YELLOW because the confirmation count is only 1.
        """
        scenario = []
        for i in range(steps):
            hour = 10 + i
            timestamp = f"2026-07-06T{hour:02d}:00:00"
            
            # Hot, dry day parameters (elevated baseline, but no individual confirmation thresholds crossed)
            if i < 2:
                sensor_data = {
                    "temperature_c": 38.0,            # Normal high: 38 < 40 (No confirmation)
                    "humidity_pct": 30.0,             # Normal dry: 30 > 25 (No confirmation)
                    "wind_speed_kmh": 12.0,           # Normal wind: 12 < 25 (No confirmation)
                    "wind_dir_deg": 180,
                    "soil_moisture_pct": 20.0,         # Normal dry: 20 > 10 (No confirmation)
                    "gas_ppm": 12.0,                  # Normal: 12 < 30 (No confirmation)
                    "thermal_anomaly_c": 0.2,         # Normal: 0.2 < 3.0 (No confirmation)
                    "light_lux": 45000,
                    "rain_mm": 0.0
                }
            # Step 2 onwards: Gas sensor fails completely and spikes
            else:
                sensor_data = {
                    "temperature_c": 39.0,            # Normal high: 39 < 40 (No confirmation)
                    "humidity_pct": 30.0,             # Normal dry: 30 > 25 (No confirmation)
                    "wind_speed_kmh": 12.0,           # Normal wind: 12 < 25 (No confirmation)
                    "wind_dir_deg": 185,
                    "soil_moisture_pct": 20.0,         # Normal dry: 20 > 10 (No confirmation)
                    "gas_ppm": 100.0,                 # Spikes to extreme level (Crosses threshold >= 30.0) -> 1 confirmation
                    "thermal_anomaly_c": 0.2,         # Normal (No confirmation)
                    "light_lux": 45000,
                    "rain_mm": 0.0
                }
                
            scenario.append({
                "timestamp": timestamp,
                "sensor_data": sensor_data,
                "seasonal_baseline": 0.8  # Dry summer baseline
            })
        return scenario

    @staticmethod
    def get_lateral_spread_scenario(steps: int = 6) -> list:
        """
        Scenario S6: Lateral Spread.
        Zone 4B escalates from GREEN -> YELLOW -> ORANGE -> RED, with wind blowing south (180 deg) toward Zone 4C.
        """
        scenario = []
        for i in range(steps):
            hour = 14 + i
            timestamp = f"2026-07-06T{hour:02d}:00:00"
            
            # Steps 0-1: Baseline green, wind blowing 180 deg (South)
            if i < 2:
                sensor_data = {
                    "temperature_c": 28.0,
                    "humidity_pct": 55.0,
                    "wind_speed_kmh": 12.0,
                    "wind_dir_deg": 180.0,
                    "soil_moisture_pct": 28.0,
                    "gas_ppm": 12.0,
                    "thermal_anomaly_c": 0.2,
                    "light_lux": 25000,
                    "rain_mm": 0.0
                }
            # Steps 2-3: Escalating fire (YELLOW -> ORANGE), wind remains 180 deg
            elif i < 4:
                sensor_data = {
                    "temperature_c": 38.0,
                    "humidity_pct": 28.0,
                    "wind_speed_kmh": 15.0,
                    "wind_dir_deg": 180.0,
                    "soil_moisture_pct": 18.0,
                    "gas_ppm": 29.0,
                    "thermal_anomaly_c": 2.5,
                    "light_lux": 24000,
                    "rain_mm": 0.0
                }
            # Steps 4-5: Full fire (RED), wind remains 180 deg
            else:
                sensor_data = {
                    "temperature_c": 48.0,
                    "humidity_pct": 12.0,
                    "wind_speed_kmh": 22.0,
                    "wind_dir_deg": 180.0,
                    "soil_moisture_pct": 8.0,
                    "gas_ppm": 85.0,
                    "thermal_anomaly_c": 7.5,
                    "light_lux": 20000,
                    "rain_mm": 0.0
                }
                
            scenario.append({
                "timestamp": timestamp,
                "sensor_data": sensor_data,
                "seasonal_baseline": 0.85
            })
        return scenario
