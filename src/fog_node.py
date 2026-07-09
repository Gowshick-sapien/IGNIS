from .scoring import normalize_reading, calculate_whi, evaluate_confirmations, evaluate_state

class FogNode:
    """
    Represents the local brain (Fog Node) for a forest division zone.
    Coordinates the execution of the modular wildfire risk decision pipeline.
    """
    def __init__(self, zone_id: str, config: dict):
        self.zone_id = zone_id
        self.config = config
        self.weights = config.get("weights", {})
        self.sensor_limits = config.get("sensor_limits", {})
        self.state_thresholds = config.get("state_thresholds", {})
        
        # Buffer to keep track of ingestion history (for future sliding window operations)
        self.history = []

    def process_reading(self, reading: dict) -> dict:
        """
        Processes a raw telemetry reading from an EdgeNode and returns a decision record.
        
        Args:
            reading (dict): The raw telemetry message from the EdgeNode.
            
        Returns:
            dict: Structured decision record outlining index calculations, confirmation state,
                  evaluated state, and triggered actions.
        """
        # Maintain local history buffer
        self.history.append(reading)
        # Cap history to last 100 readings for memory sanity in this simulation
        if len(self.history) > 100:
            self.history.pop(0)
            
        # 1. Normalize raw reading
        normalized = normalize_reading(reading, self.sensor_limits)
        
        # 2. Compute Wildfire Hazard Index (WHI)
        whi = calculate_whi(normalized, self.weights)
        
        # 3. Evaluate Sensor Confirmations (False Positive mitigation)
        confirming_sensors, confirmation_count = evaluate_confirmations(reading, self.sensor_limits)
        
        # 4. Determine Risk State (evaluates thresholds and confirmation counts)
        state, is_clamped = evaluate_state(whi, confirmation_count, self.state_thresholds)
        
        # 5. Determine Autonomous Actions based on final state
        actions_logged = []
        if state == "ORANGE":
            actions_logged = ["activate_mist_perimeter", "notify_control_center"]
        elif state == "RED":
            actions_logged = [
                "escalate_pre_suppression_to_max",
                "emergency_alert_control_center",
                "broadcast_lateral_orange"
            ]
            
        # 6. Format and return structured decision record (no console side effects)
        decision_record = {
            "zone_id": self.zone_id,
            "timestamp": reading.get("timestamp"),
            "whi": whi,
            "confirmation_count": confirmation_count,
            "confirming_sensors": confirming_sensors,
            "state": state,
            "is_state_clamped": is_clamped,
            "actions_logged": actions_logged,
            "cloud_connected": False,  # No cloud link in Phase A
            "raw_reading": reading,
            "normalized_reading": normalized
        }
        
        return decision_record
