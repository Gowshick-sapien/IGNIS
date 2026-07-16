import os
import sys
import unittest
import shutil
import yaml

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scenarios.yaml_validator import YamlValidator

class TestYamlValidator(unittest.TestCase):
    
    def setUp(self):
        self.validator = YamlValidator()
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_test_scenarios"))
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Valid base YAML configuration
        self.valid_base = {
            "scenario_id": "STest",
            "description": "Test Scenario Description",
            "version": "1.0",
            "target": {
                "mode": "localized",
                "zone_ids": ["4B"]
            },
            "steps": [
                {
                    "index": 0,
                    "duration_sec": 4,
                    "sensor_data": {
                        "temperature_c": 28.0
                    },
                    "seasonal_baseline": 0.3
                }
            ],
            "expected_outcome": {
                "final_state": "GREEN",
                "max_state_allowed": "GREEN",
                "is_clamped": False
            },
            "metrics_targets": {},
            "validation": {
                "require_events": True,
                "min_event_count": 1,
                "timeout_sec": 60,
                "assertions": [
                    {
                        "metric": "max_state",
                        "operator": "==",
                        "threshold": "GREEN"
                    }
                ]
            }
        }

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def write_temp_yaml(self, filename: str, data: dict) -> str:
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        return filepath

    def test_valid_scenarios_pass(self):
        # Validate all seven production YAML files in /scenarios
        results = self.validator.validate_all("scenarios")
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertTrue(
                r["valid"],
                f"Production scenario failed validation: Errors = {r['errors']}"
            )

    def test_missing_required_keys(self):
        # Omit 'validation' key
        bad_data = self.valid_base.copy()
        del bad_data["validation"]
        filepath = self.write_temp_yaml("missing_key.yaml", bad_data)
        
        res = self.validator.validate(filepath)
        self.assertFalse(res["valid"])
        self.assertTrue(any("Missing required key" in err for err in res["errors"]))

    def test_invalid_assertion_operator(self):
        # Use an invalid operator
        bad_data = self.valid_base.copy()
        bad_data["validation"] = {
            "require_events": True,
            "min_event_count": 1,
            "timeout_sec": 60,
            "assertions": [
                {
                    "metric": "max_state",
                    "operator": "=>", # Invalid operator
                    "threshold": "GREEN"
                }
            ]
        }
        filepath = self.write_temp_yaml("invalid_op.yaml", bad_data)
        
        res = self.validator.validate(filepath)
        self.assertFalse(res["valid"])
        self.assertTrue(any("invalid operator" in err for err in res["errors"]))

    def test_invalid_types(self):
        # Use a string instead of an integer for timeout_sec
        bad_data = self.valid_base.copy()
        bad_data["validation"] = {
            "require_events": True,
            "min_event_count": 1,
            "timeout_sec": "sixty", # Invalid type
            "assertions": []
        }
        filepath = self.write_temp_yaml("invalid_type.yaml", bad_data)
        
        res = self.validator.validate(filepath)
        self.assertFalse(res["valid"])
        self.assertTrue(any("must be an integer" in err for err in res["errors"]))

    def test_checksum_integrity(self):
        # Write first file
        filepath = self.write_temp_yaml("checksum_test.yaml", self.valid_base)
        checksum_before = self.validator.checksum(filepath)
        
        # Modify the description slightly
        modified_data = self.valid_base.copy()
        modified_data["description"] = "Test Scenario Description Modified"
        self.write_temp_yaml("checksum_test.yaml", modified_data)
        checksum_after = self.validator.checksum(filepath)
        
        self.assertNotEqual(checksum_before, checksum_after)

    def test_invalid_file_not_found(self):
        res = self.validator.validate(os.path.join(self.temp_dir, "non_existent_file.yaml"))
        self.assertFalse(res["valid"])
        self.assertTrue(any("File not found" in err for err in res["errors"]))

    def test_non_dict_root(self):
        filepath = os.path.join(self.temp_dir, "list_root.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(["item1", "item2"], f)
        
        res = self.validator.validate(filepath)
        self.assertFalse(res["valid"])
        self.assertTrue(any("must be a dictionary" in err for err in res["errors"]))

if __name__ == "__main__":
    unittest.main()
