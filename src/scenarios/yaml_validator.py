import os
import glob
import hashlib
import yaml

class YamlValidator:
    REQUIRED_KEYS = [
        "scenario_id",
        "description",
        "version",
        "target",
        "steps",
        "expected_outcome",
        "metrics_targets",
        "validation"
    ]
    
    VALID_OPERATORS = ["<=", "==", "<", ">=", ">", "!="]

    def validate(self, yaml_path: str) -> dict:
        """
        Parses and validates a single scenario YAML file.
        Returns:
            dict: {"valid": bool, "errors": list, "warnings": list, "scenario_id": str or None}
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "scenario_id": None
        }

        if not os.path.exists(yaml_path):
            result["valid"] = False
            result["errors"].append(f"File not found: {yaml_path}")
            return result

        # 1. Parse YAML file
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"YAML parsing error: {e}")
            return result

        if not isinstance(data, dict):
            result["valid"] = False
            result["errors"].append("YAML root element must be a dictionary")
            return result

        # Extract scenario_id if present
        scenario_id = data.get("scenario_id")
        result["scenario_id"] = scenario_id

        # 2. Check required keys
        for key in self.REQUIRED_KEYS:
            if key not in data:
                result["valid"] = False
                result["errors"].append(f"Missing required key: '{key}'")

        if not result["valid"]:
            return result

        # 3. Validate 'target' key
        target = data.get("target")
        if not isinstance(target, dict):
            result["errors"].append("'target' must be a dictionary")
        else:
            mode = target.get("mode")
            if mode not in ["global", "localized", "multi_zone"]:
                result["errors"].append(f"Invalid target mode: '{mode}' (must be 'global', 'localized', or 'multi_zone')")
            zone_ids = target.get("zone_ids")
            if not isinstance(zone_ids, list):
                result["errors"].append("'target.zone_ids' must be a list")

        # 4. Validate 'steps' key
        steps = data.get("steps")
        if not isinstance(steps, list):
            result["errors"].append("'steps' must be a list")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    result["errors"].append(f"Step at index {i} must be a dictionary")
                    continue
                for step_key in ["index", "duration_sec", "sensor_data", "seasonal_baseline"]:
                    if step_key not in step:
                        result["errors"].append(f"Step {i} missing required key: '{step_key}'")
                
                # Check sensor_data structure if present
                sensor_data = step.get("sensor_data")
                if sensor_data is not None and not isinstance(sensor_data, dict):
                    result["errors"].append(f"Step {i} 'sensor_data' must be a dictionary")

        # 5. Validate 'expected_outcome' key
        expected_outcome = data.get("expected_outcome")
        if not isinstance(expected_outcome, dict):
            result["errors"].append("'expected_outcome' must be a dictionary")
        else:
            final_state = expected_outcome.get("final_state")
            if final_state not in ["GREEN", "YELLOW", "ORANGE", "RED"]:
                result["errors"].append(f"Invalid final_state: '{final_state}'")
            max_state = expected_outcome.get("max_state_allowed")
            if max_state not in ["GREEN", "YELLOW", "ORANGE", "RED"]:
                result["errors"].append(f"Invalid max_state_allowed: '{max_state}'")
            if not isinstance(expected_outcome.get("is_clamped"), bool):
                result["errors"].append("'expected_outcome.is_clamped' must be a boolean")

        # 6. Validate 'metrics_targets' key
        metrics_targets = data.get("metrics_targets")
        if not isinstance(metrics_targets, dict):
            result["errors"].append("'metrics_targets' must be a dictionary")

        # 7. Validate 'validation' block
        validation = data.get("validation")
        if not isinstance(validation, dict):
            result["errors"].append("'validation' must be a dictionary")
        else:
            if not isinstance(validation.get("require_events"), bool):
                result["errors"].append("'validation.require_events' must be a boolean")
            if not isinstance(validation.get("min_event_count"), int):
                result["errors"].append("'validation.min_event_count' must be an integer")
            if not isinstance(validation.get("timeout_sec"), int):
                result["errors"].append("'validation.timeout_sec' must be an integer")
            
            assertions = validation.get("assertions")
            if not isinstance(assertions, list):
                result["errors"].append("'validation.assertions' must be a list")
            else:
                for idx, assertion in enumerate(assertions):
                    if not isinstance(assertion, dict):
                        result["errors"].append(f"Assertion {idx} must be a dictionary")
                        continue
                    
                    # check keys
                    for ast_key in ["metric", "operator", "threshold"]:
                        if ast_key not in assertion:
                            result["errors"].append(f"Assertion {idx} missing required key: '{ast_key}'")
                    
                    # check operator
                    op = assertion.get("operator")
                    if op not in self.VALID_OPERATORS:
                        result["errors"].append(
                            f"Assertion {idx} invalid operator: '{op}' (must be one of {self.VALID_OPERATORS})"
                        )

        if result["errors"]:
            result["valid"] = False

        return result

    def validate_all(self, scenarios_dir: str = "scenarios") -> list[dict]:
        """
        Validates all YAML files in the given directory.
        """
        results = []
        yaml_pattern = os.path.join(scenarios_dir, "*.yaml")
        yaml_files = glob.glob(yaml_pattern)
        for yaml_path in sorted(yaml_files):
            results.append(self.validate(yaml_path))
        return results

    def checksum(self, yaml_path: str) -> str:
        """
        Computes SHA-256 checksum of the target YAML file in binary mode.
        """
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"File not found: {yaml_path}")
        
        hasher = hashlib.sha256()
        with open(yaml_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def checksum_all(self, scenarios_dir: str = "scenarios") -> dict[str, str]:
        """
        Returns a dictionary mapping scenario_id to its SHA-256 checksum.
        """
        checksums = {}
        yaml_pattern = os.path.join(scenarios_dir, "*.yaml")
        yaml_files = glob.glob(yaml_pattern)
        for yaml_path in sorted(yaml_files):
            try:
                # We validate first to ensure scenario_id can be extracted
                val = self.validate(yaml_path)
                scenario_id = val.get("scenario_id")
                if scenario_id:
                    checksums[scenario_id] = self.checksum(yaml_path)
            except Exception:
                pass
        return checksums
