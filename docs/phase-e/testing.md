# Phase E Consolidated Testing: Fault & Chaos Resilience Testing

This document details the consolidated testing approach, test cases, and execution guidelines for Phase E (Fault & Chaos Resilience Testing).

## Testing Strategy

To verify the components of Phase E safely and deterministically inside a standard CI/CD environment without requiring a running Docker daemon, live network partitions, or standard time delays, we use the following testing patterns:
1. **MockClock**: Managed simulated clock progressions inside unit tests. Tests can fast-forward time to assert TTL and buffering timeouts in milliseconds rather than minutes.
2. **Mock MQTT Client**: Bypasses network traffic using mocked connection handles, storing published topics and payloads in memory.
3. **Mocked REST Calls**: Intercepts outgoing `requests.post` REST API calls using `unittest.mock.patch` to verify correct payload parameter values and offsets.
4. **Mocked Docker SDK Client**: Simulates networks list, container lookups, stop operations, and network disconnections.
5. **FastAPI TestClient**: Executes API routing calls locally without spinning up web server sockets.

---

## Unit Test Cases (`tests/test_chaos_resilience.py`)

### 1. Phase E1: Foundations
- `test_decision_event_serialization`: Verifies event serialization/deserialization.
- `test_mock_clock_time`: Verifies simulated clock time tracking and increments.
- `test_mock_clock_sleep`: Verifies mock clock sleep intervals logging.
- `test_buffered_publisher_publish_connected`: Verifies direct message publication when connected.
- `test_buffered_publisher_publish_disconnected`: Verifies message caching when offline.
- `test_buffered_publisher_flush`: Verifies that cached records are successfully drained on reconnect.
- `test_buffered_publisher_buffer_overflow`: Verifies that the publisher respects the maximum buffer threshold.
- `test_scenario_service_resolution`: Verifies that scenario service resolves zone-prefixed node indices dynamically.

### 2. Phase E2: Fog Node Cloud-Disconnect Resilience
- `test_fog_runner_offline_queuing`: Verifies that telemetry and state payloads are cached when the fog runner goes offline.
- `test_fog_runner_reconnect_flush`: Verifies that cached payloads flush automatically upon reconnecting.
- `test_fog_runner_offline_continuity_logging`: Verifies that ORANGE/RED local mitigations generate stdout offline continuity logs.

### 3. Phase E3: YAML Scenario Library & Package
- `test_registry_resolution`: Verifies that all scenario IDs (`S1` to `S7`) successfully resolve in the registry.
- `test_yaml_schema_conformance`: Verifies that YAML files load successfully and contain standard schema properties.
- `test_scenario_runner_execution`: Runs S4, intercepts publications, and validates the expected outcomes.

### 4. Phase E4: Chaos Controller Service
- `test_routes_endpoints`: Runs a test FastAPI client and validates all routes return success responses and pass correct container target requests to `DockerAdapter`.
- `test_docker_adapter_methods`: Verifies `disconnect`, `connect`, `stop`, and `restart` docker APIs execute correctly under mocked container and network clients.

### 5. Phase E5: Scenario Automation with Fault Injection
- `test_scenario_s5_execution`: Asserts that running S5 triggers a `disconnect_cloud` POST request to the Chaos Controller at the correct offset (t=8s).
- `test_scenario_s7_concurrent_execution`: Runs S7 in parallel and asserts that merged logs contain execution entries for both zone threads (`S7-4A` and `S7-4B`) and zone IDs `["4A", "4B"]`.

### 6. Phase E6: Metrics Collector & Report Generator
- `test_metrics_calculation_logic`: Verifies that averages, propagation times, false positive counts, and buffering limits are computed accurately.
- `test_report_generator`: Plugs mocked saved figures and file opening handles to verify Matplotlib renders and report creation.

### 7. Phase E7: Tests, Dashboard, Documentation
- `test_dashboard_metrics_routes`: Runs FastAPI TestClient checks against the Cloud Dashboard service to ensure `/api/metrics/latest` and `/metrics` return status code 200 without database connection blocks.

---

## Verification Execution

### 1. Run Resilience Test Suite
Run the chaos resilience test cases from the project root:
```powershell
python -m unittest tests/test_chaos_resilience.py
```

### 2. Run Full Test Suite
To verify that all changes do not cause regression issues in the legacy modules:
```powershell
python -m unittest discover tests
```
All 52 tests in the repository will be executed and should pass cleanly.

---

## Manual Testing

This section describes the end-to-end steps to verify the entire Phase E implementation manually, from container execution to live fault injection and metrics dashboards.

### Prerequisite: Startup the Environment
1. Ensure **Docker Desktop** is running.
2. Start the Docker containers from the project root:
   ```powershell
   docker compose up --build -d
   ```
3. Start the Chaos Controller host service (port 9001):
   ```powershell
   python -m src.chaos_controller.app
   ```
4. Start the Central Cloud Dashboard (port 9000):
   ```powershell
   python -m uvicorn src.cloud_dashboard.app:app --host 0.0.0.0 --port 9000
   ```

### 1. Verification of Metrics and Report Generation
1. Run the Metrics Collector CLI to execute scenario trials:
   ```powershell
   python -m src.metrics_collector --results-dir results --trials 5
   ```
   This generates the raw trial output (`results/raw_results.json`) and calculated results (`results/metrics.json`).
2. Run the Report Generator CLI to compile the charts and write the report:
   ```powershell
   python -m src.report_generator --results-dir results
   ```
   Verify that:
   - Five visualization PNGs are generated inside `docs/phase-e/charts/`.
   - The dissertation-ready report [section7_metrics_report.md](file:///D:/projects/IGNIS/docs/phase-e/section7_metrics_report.md) is written.

### 2. Verification of NOC Metrics View
1. Open your browser and navigate to `http://localhost:9000/metrics`.
2. Verify that:
   - The decision latency values, propagation times, false positive rate progress bar, and flush success rate match your trial results.
   - The five Matplotlib charts are rendered successfully.
   - The Active Fault Injection status card lists Zone 4A, Zone 4B, and Node 4B container status as **Normal** or **Running**.

### 3. Verification of Live Fault Injection
1. While keeping the browser open on the `/metrics` page, open a separate terminal and inject a cloud network disconnect fault for Zone 4B:
   ```powershell
   Invoke-RestMethod -Uri http://localhost:9001/api/chaos/disconnect_cloud -Method Post -ContentType "application/json" -Body '{"zone_id": "4B", "duration_sec": 20}'
   ```
2. Observe the Active Fault Injection status card in the browser:
   - Verify that the card dynamically updates to show Zone 4B network status as **Disconnected** with a vibrant red badge.
   - After 20 seconds, verify that the status automatically reverts to **Normal** (verifying background auto-restoration).

