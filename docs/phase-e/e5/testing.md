# Phase E5 Testing: Scenario Automation with Fault Injection

This document outlines the testing strategy, test cases, and execution procedures for Phase E5 (Scenario Automation with Fault Injection).

## Test Strategy

To verify scenario fault injection and concurrent multi-threading, we execute unit tests using the `MockClock` and in-memory mock MQTT clients, and patch the outgoing REST API `requests.post` calls to the Chaos Controller.

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Scenario S5 Fault Injection (`test_scenario_s5_execution`)
- **Objective**: Verify that S5 triggers a `disconnect_cloud` REST POST call to the Chaos Controller at the correct timeline offset (after 8 simulated seconds).
- **Procedure**:
  1. Patch `requests.post` and the standard node reset helper.
  2. Setup `ScenarioRunner` using `MockClock`.
  3. Side-effect the MQTT client's publish method to inject mock state reports.
  4. Run scenario `S5` for 1 trial.
  5. Assert that `ScenarioResult.passed` is `True`.
  6. Assert that `requests.post` was called with the endpoint `/api/chaos/disconnect_cloud`, passing parameters `{zone_id: "4B", duration_sec: 20}`.

### 2. Scenario S7 Concurrent Execution (`test_scenario_s7_concurrent_execution`)
- **Objective**: Verify that S7 executes parallel threads for multiple zones concurrently, and aggregates results.
- **Procedure**:
  1. Setup `ScenarioRunner` using `MockClock`.
  2. Side-effect publish call to inject state reports.
  3. Run scenario `S7` for 1 trial.
  4. Assert that `ScenarioResult.passed` is `True`.
  5. Assert that `zone_ids` contains both `4A` and `4B`.
  6. Assert that merged logs contain execution entries for both parallel threads: `"Starting scenario S7-4A"` and `"Starting scenario S7-4B"`.

---

## Verification Execution

### Run Chaos Controller Unit Tests
Run the chaos resilience test cases from the project root:
```powershell
python -m unittest tests/test_chaos_resilience.py
```

### Run Full Test Suite
To verify that the service changes do not cause regression issues in the other modules:
```powershell
python -m unittest discover tests
```
