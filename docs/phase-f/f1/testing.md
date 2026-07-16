# Phase F1 Testing: YAML Scenario Schema Hardening

This document outlines the testing strategy, test cases, and execution procedures for Phase F1 (YAML Scenario Schema Hardening).

---

## Test Strategy

The verification utility is validated using Python's `unittest` framework. By using a temporary scenario directory, tests are written to verify that both valid configurations and malformed schema definitions (e.g. missing keys, invalid operators, wrong variable types) are detected accurately. Additionally, SHA-256 hashes are evaluated for sensitivity to modifications.

---

## Test Cases Defined (`tests/test_yaml_validator.py`)

### 1. Production Scenario Validation
- **`test_valid_scenarios_pass`**: Iterates over all seven active scenario YAML files in the `scenarios/` directory. Ensures they all pass schema checks with zero errors.

### 2. Missing Key Detection
- **`test_missing_required_keys`**: Omit a vital key (such as `validation`) from the config dictionary and write it to a temp path. Verifies that validation fails and reports the missing key error.

### 3. Operator Constraint Enforcement
- **`test_invalid_assertion_operator`**: Feeds an unsupported operator (like `=>`) in the validation assertions array. Asserts that the validation output flag is `False` and lists the invalid operator error.

### 4. Type Restriction Verification
- **`test_invalid_types`**: Modifies the `timeout_sec` configuration to be a string instead of an integer. Asserts that validation fails and rejects the type discrepancy.

### 5. Integrity & Provenance Checksumming
- **`test_checksum_integrity`**: Writes a temp scenario file, calculates its SHA-256 hex digest, modifies a single character in the file content, re-calculates the digest, and asserts that the two hashes are different.

### 6. Boundary Failures
- **`test_invalid_file_not_found`**: Tries to validate a file path that doesn't exist and expects clean, non-crashing failure reports.
- **`test_non_dict_root`**: Validates a file that does not have a root dictionary structure (e.g. root list) and expects type failure reports.

---

## Verification Execution

### Run F1 Unit Tests
To run the Phase F1 test suite:
```powershell
python -m unittest tests/test_yaml_validator.py
```

### Run Full Test Suite
To verify that F1 changes do not introduce regressions into other modules:
```powershell
python -m unittest discover tests
```
