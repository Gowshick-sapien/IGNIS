# Phase E3 Testing: YAML Scenario Library & Scenario Package

This document outlines the testing strategy, test cases, and execution procedures for Phase E3 (YAML Scenario Library & Scenario Package).

## Test Strategy

To verify the scenario registry, parser logic, and runner outcomes, we use unit tests that parse actual YAML files on the filesystem and execute simulated MQTT loop runs. 

Dependencies:
- `pyyaml` (Installed on the system to parse YAML files).

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Registry Resolution (`test_registry_resolution`)
- **Objective**: Verify that all scenario identifiers successfully map to valid implementations.
- **Procedure**:
  1. Iterate over scenario IDs `S1` through `S7`.
  2. Verify that each ID exists in `SCENARIO_REGISTRY`.
  3. Assert that the resolved class is a subclass of `BaseScenario`.

### 2. YAML Schema Conformance (`test_yaml_schema_conformance`)
- **Objective**: Verify that all YAML files are well-formed and conform to the standard structure.
- **Procedure**:
  1. Discover all files matching `scenarios/s*.yaml`.
  2. Assert that at least 7 scenario files are found.
  3. Load and parse each file.
  4. Assert that keys `scenario_id`, `target`, `steps`, and `expected_outcome` exist in the parsed dictionaries.

### 3. Scenario Runner Execution (`test_scenario_runner_execution`)
- **Objective**: Verify that `ScenarioRunner` handles step execution, captures MQTT events, and validates outcomes correctly.
- **Procedure**:
  1. Instantiate `ScenarioRunner` with a `MockClock`.
  2. Mock the MQTT client's `connect()`, `publish()`, and loop methods.
  3. Side-effect the client's `publish()` call to append a mock state event payload representing a clamped state.
  4. Run scenario `S4` for 1 trial.
  5. Assert that a single `ScenarioResult` is returned.
  6. Assert that `passed` is `True` (since the mock event matches `S4`'s clamping expectation).
  7. Assert that events were successfully captured in the result.

---

## Verification Execution

### Run Scenario Unit Tests
Run the chaos resilience test cases from the project root:
```powershell
python -m unittest tests/test_chaos_resilience.py
```

### Run Full Test Suite
To verify that the scenario changes do not cause regression issues in the other modules:
```powershell
python -m unittest discover tests
```
