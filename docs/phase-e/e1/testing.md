# Phase E1 Testing: Foundations

This document outlines the testing strategy, test cases, and execution procedures for Phase E1 (Foundations).

## Test Strategy

All foundation modules are unit tested using in-memory mock clients and mock clocks to verify logical correctness, thread safety, and serialization compatibility. The test suite does not require a running external MQTT broker or active databases.

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Clock Mockability
- **`test_clock_production`**: Verifies that the production `Clock` successfully retrieves real-world time, executes real sleep processes, and produces correctly formatted UTC timestamps (`%Y-%m-%dT%H:%M:%SZ`).
- **`test_mock_clock_deterministic`**: Verifies that `MockClock` behaves deterministically. Ensures `advance()` and `sleep()` increment the epoch correctly, and time-formatting produces exact, reproducible timestamp strings in UTC.

### 2. Event Model Serialization
- **`test_decision_event`**, **`test_alert_event`**, **`test_action_event`**, **`test_cloud_report_event`**, **`test_scenario_event`**: Verifies round-trip compatibility of each dataclass model. Checks that serializing with `to_dict()` and reconstructing with `from_dict()` preserves type accuracy and parameter values.

### 3. Reusable Buffered Publisher
- **`test_buffered_publisher_queuing`**: Confirms that when disconnected, messages are appended to the internal buffer and the call returns `False` indicating it was not dispatched immediately.
- **`test_buffered_publisher_flush`**: Validates that when connectivity is restored, calling `flush()` publishes all buffered items in sequential, first-in-first-out (FIFO) order, and returns the correct count of flushed messages.
- **`test_buffered_publisher_overflow`**: Verifies that the O(1) buffer evicts the oldest message once the maximum length (`maxlen`) is exceeded.
- **`test_buffered_publisher_publish_success`**: Assumes immediate dispatch when connected, resulting in no buffering.
- **`test_buffered_publisher_publish_failure_queuing`**: Simulates a broker error where connection is active but publish fails (rc != 0). Ensures the message is correctly enqueued for later delivery.

### 4. Scenario Service Node Resolution
- **`test_localized_scenario_node_resolution`**: Mocks the MQTT publisher client within `ScenarioService` and targets the localized scenario runs. Asserts that control signals are sent dynamically to the zone-prefixed node identifiers (`4B-E1`, `4B-E2`, `4B-E3`) instead of the hardcoded legacy nodes (`E11`, `E12`, `E13`).

---

## Verification Execution

### Run Foundation Unit Tests
Run the specific suite from the repository root:
```powershell
python -m unittest tests/test_chaos_resilience.py
```

### Run Full Test Suite
To confirm no regressions have occurred across existing modules:
```powershell
python -m unittest discover tests
```
