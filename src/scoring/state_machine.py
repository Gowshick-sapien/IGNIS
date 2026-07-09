def evaluate_state(whi: float, confirmation_count: int, state_thresholds: dict) -> tuple:
    """
    Evaluates and returns the wildfire risk state based on WHI and confirmation count.
    
    Rules:
    - RED: WHI >= RED_threshold AND confirmation_count >= 3
    - ORANGE: WHI >= ORANGE_threshold AND confirmation_count >= 3
    - YELLOW: WHI >= YELLOW_threshold
    - GREEN: default
    
    If WHI exceeds ORANGE or RED threshold but confirmation_count < 3, the state is
    clamped/downgraded to YELLOW to prevent false positives from sensor faults.
    
    Returns:
        tuple: (state_name as str, is_clamped as bool)
    """
    yellow_thresh = state_thresholds.get("YELLOW", 0.35)
    orange_thresh = state_thresholds.get("ORANGE", 0.60)
    red_thresh = state_thresholds.get("RED", 0.80)
    
    raw_state = "GREEN"
    if whi >= red_thresh:
        raw_state = "RED"
    elif whi >= orange_thresh:
        raw_state = "ORANGE"
    elif whi >= yellow_thresh:
        raw_state = "YELLOW"
        
    # Check confirmation constraints for ORANGE and RED
    if raw_state in ("ORANGE", "RED"):
        if confirmation_count >= 3:
            return raw_state, False
        else:
            # Clamping behavior active
            return "YELLOW", True
            
    return raw_state, False
