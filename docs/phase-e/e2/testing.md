# Phase E2 Testing: Fog Node Cloud-Disconnect Resilience

This document outlines the testing strategy, test cases, and execution procedures for Phase E2 (Fog Node Cloud-Disconnect Resilience).

## Test Strategy

To verify the buffering, reconnect, flushing, and continuity logs, we use the `MockClock` and in-memory mock MQTT clients. This allows us to trigger simulated disconnections and verify that the runner behaves correctly without requiring physical network outages or container manipulation.

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Fog Runner Offline Queuing (`test_fog_runner_offline_queuing`)
- **Objective**: Verify that telemetry and state updates are successfully buffered when the fog node is disconnected from the cloud.
- **Procedure**:
  1. Initialize `FogNodeRunner` with a `MockClock`.
  2. Set connection state to offline (default).
  3. Send a simulated local edge message using `on_message_local()`.
  4. Assert that `runner.cloud_publisher.buffer_size` equals `4` (queuing the telemetry payload, state payload, alert, and lateral wind broadcast).
  5. Assert that no raw publish commands were dispatched directly to the broker.

### 2. Fog Runner Reconnect Flush (`test_fog_runner_reconnect_flush`)
- **Objective**: Verify that buffered telemetry is automatically flushed when connection is restored.
- **Procedure**:
  1. Load and queue messages while offline (buffer size = 4).
  2. Simulate reconnection by calling `on_connect_cloud(rc=0)`.
  3. Assert that the publisher's queue size is drained to `0`.
  4. Assert that all 4 messages were successfully published to the mock MQTT client.

### 3. Offline Continuity Logging (`test_fog_runner_offline_continuity_logging`)
- **Objective**: Validate that action records are logged locally to stdout when offline during emergency transitions.
- **Procedure**:
  1. Trigger an edge reading that causes an escalation to `RED` state (using high temperatures, low humidity, high wind, and active anomalies).
  2. Capture the logging stdout using `self.assertLogs`.
  3. Assert that `[Offline Continuity] Action Log:` is printed in the info log stream, verifying local continuity.

---

## Verification Execution

### Run Resilience Unit Tests
Run the chaos resilience test cases:
```powershell
python -m unittest tests/test_chaos_resilience.py
```

### Run Full Test Suite
Run the full test suite to guarantee that fallback properties maintain backward compatibility with legacy mocked classes:
```powershell
python -m unittest discover tests
```
