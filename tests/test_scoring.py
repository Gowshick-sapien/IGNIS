import unittest
import sys
import os

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scoring.normalization import normalize_value, normalize_time_of_day, normalize_reading
from src.scoring.hazard_index import calculate_whi
from src.scoring.confirmation import evaluate_confirmations
from src.scoring.state_machine import evaluate_state


class TestScoringModules(unittest.TestCase):
    
    def setUp(self):
        # Sample configuration mimicking config/zone_config.json
        self.sensor_limits = {
            "temperature_c": {"min": 20.0, "max": 45.0, "confirmation_threshold": 40.0},
            "humidity_pct": {"min": 15.0, "max": 70.0, "confirmation_threshold": 25.0},
            "wind_speed_kmh": {"min": 0.0, "max": 40.0, "confirmation_threshold": 25.0},
            "soil_moisture_pct": {"min": 5.0, "max": 35.0, "confirmation_threshold": 10.0},
            "gas_ppm": {"min": 10.0, "max": 100.0, "confirmation_threshold": 30.0},
            "thermal_anomaly_c": {"min": 0.0, "max": 10.0, "confirmation_threshold": 3.0}
        }
        
        self.weights = {
            "temperature_c": 0.20,
            "humidity_pct": 0.15,
            "wind_speed_kmh": 0.10,
            "soil_moisture_pct": 0.15,
            "gas_ppm": 0.15,
            "thermal_anomaly_c": 0.15,
            "time_of_day": 0.05,
            "seasonal_baseline": 0.05
        }
        
        self.state_thresholds = {
            "GREEN": 0.0,
            "YELLOW": 0.35,
            "ORANGE": 0.60,
            "RED": 0.80
        }

    def test_normalization_bounds(self):
        # Standard value scaling
        self.assertEqual(normalize_value(20.0, 20.0, 45.0), 0.0)
        self.assertEqual(normalize_value(45.0, 20.0, 45.0), 1.0)
        # Clamping
        self.assertEqual(normalize_value(15.0, 20.0, 45.0), 0.0)
        self.assertEqual(normalize_value(50.0, 20.0, 45.0), 1.0)
        # Invert (humidity/soil moisture)
        self.assertEqual(normalize_value(15.0, 15.0, 70.0, invert=True), 1.0)
        self.assertEqual(normalize_value(70.0, 15.0, 70.0, invert=True), 0.0)

    def test_time_of_day_normalization(self):
        # Peaks at 14:00 (1.0)
        self.assertEqual(normalize_time_of_day(14), 1.0)
        # Lowest at 02:00 (0.0)
        self.assertEqual(normalize_time_of_day(2), 0.0)
        self.assertAlmostEqual(normalize_time_of_day(8), 0.5)

    def test_hazard_index_computation(self):
        normalized = {
            "temperature_c": 0.5,
            "humidity_pct": 0.5,
            "wind_speed_kmh": 0.5,
            "soil_moisture_pct": 0.5,
            "gas_ppm": 0.5,
            "thermal_anomaly_c": 0.5,
            "time_of_day": 0.5,
            "seasonal_baseline": 0.5
        }
        # Since all parameters are 0.5 and weights sum to 1.0, WHI should be 0.5
        whi = calculate_whi(normalized, self.weights)
        self.assertAlmostEqual(whi, 0.5)

    def test_confirmations_count(self):
        # Case where 2 sensors cross threshold
        reading = {
            "temperature_c": 42.0,      # Crosses (>= 40.0)
            "humidity_pct": 30.0,       # Does not cross (needs <= 25.0)
            "wind_speed_kmh": 10.0,     # Does not cross (needs >= 25.0)
            "soil_moisture_pct": 15.0,  # Does not cross (needs <= 10.0)
            "gas_ppm": 35.0,            # Crosses (>= 30.0)
            "thermal_anomaly_c": 1.0    # Does not cross (needs >= 3.0)
        }
        confirming, count = evaluate_confirmations(reading, self.sensor_limits)
        self.assertEqual(count, 2)
        self.assertIn("temperature_c", confirming)
        self.assertIn("gas_ppm", confirming)

    def test_state_machine_clamping(self):
        # Case A: WHI high (0.85), but confirmations = 2. Should clamp to YELLOW.
        state, is_clamped = evaluate_state(0.85, 2, self.state_thresholds)
        self.assertEqual(state, "YELLOW")
        self.assertTrue(is_clamped)
        
        # Case B: WHI high (0.85) and confirmations = 3. Should stay RED.
        state, is_clamped = evaluate_state(0.85, 3, self.state_thresholds)
        self.assertEqual(state, "RED")
        self.assertFalse(is_clamped)

        # Case C: WHI medium-high (0.65) and confirmations = 1. Should clamp to YELLOW.
        state, is_clamped = evaluate_state(0.65, 1, self.state_thresholds)
        self.assertEqual(state, "YELLOW")
        self.assertTrue(is_clamped)

        # Case D: WHI medium (0.45). Should be YELLOW, not clamped (since threshold matches).
        state, is_clamped = evaluate_state(0.45, 1, self.state_thresholds)
        self.assertEqual(state, "YELLOW")
        self.assertFalse(is_clamped)

        # Case E: WHI low (0.20). Should be GREEN.
        state, is_clamped = evaluate_state(0.20, 0, self.state_thresholds)
        self.assertEqual(state, "GREEN")
        self.assertFalse(is_clamped)


if __name__ == '__main__':
    unittest.main()
