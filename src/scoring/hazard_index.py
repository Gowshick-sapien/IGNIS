def calculate_whi(normalized_readings: dict, weights: dict) -> float:
    """
    Computes the Wildfire Hazard Index (WHI) as the weighted sum of normalized parameters.
    Returns a score between [0.0, 1.0].
    """
    whi = 0.0
    for key, weight in weights.items():
        val = normalized_readings.get(key, 0.0)
        whi += val * weight
        
    return max(0.0, min(1.0, whi))
