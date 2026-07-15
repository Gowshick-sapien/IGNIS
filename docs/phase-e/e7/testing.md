# Phase E7 Testing: Tests, Dashboard, Documentation

This document outlines the testing strategy, test cases, and execution procedures for Phase E7 (Dashboard and Metrics Integration).

## Testing Strategy

To verify the integration routes safely without running real InfluxDB databases or socket listeners:
1. **Mocked Lifespan connection**: We patch `connect` and `close` methods on the database wrapper during `TestClient(app)` execution, allowing the uvicorn lifespan to start instantly.
2. **Mocked Influx client**: We patch `sys.modules['influxdb_client']` with a mock handle to prevent any missing module or import errors in non-docker test environments.
3. **HTTP Route Assertion**: We execute HTTP requests against the FastAPI app instance and assert correct status codes and payload contents.

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Dashboard Metrics Routing (`test_dashboard_metrics_routes`)
- **Objective**: Verify that metrics endpoint `/api/metrics/latest` and HTML route `/metrics` are accessible.
- **Procedure**:
  1. Patch `CloudDashboardDB.connect` and `close`.
  2. Instantiate `TestClient(app)` using context-management.
  3. Perform `GET /api/metrics/latest`. Assert status `200 OK` and JSON keys `decision_latency` exist.
  4. Perform `GET /metrics`. Assert status `200 OK` and response body contains text `"IGNIS"`.

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
All 52 tests in the repository will execute and pass cleanly.

---

## Manual E2E Walkthrough

1. **Spin up Compose Network**:
   ```powershell
   docker compose up -d
   ```
2. **Launch Chaos Controller**:
   ```powershell
   python -m src.chaos_controller.app
   ```
3. **Launch Cloud Dashboard**:
   ```powershell
   python -m uvicorn src.cloud_dashboard.app:app --host 0.0.0.0 --port 9000
   ```
4. Navigate to `http://localhost:9000/metrics` in the browser. Verify cards load and charts are embedded.
5. In a separate shell, sever Zone 4B's cloud broker connection:
   ```powershell
   Invoke-RestMethod -Uri http://localhost:9001/api/chaos/disconnect_cloud -Method Post -ContentType "application/json" -Body '{"zone_id": "4B", "duration_sec": 20}'
   ```
6. Observe the Active Fault Injection card on the metrics page. Verify that it dynamically updates to show Zone 4B network status as "Disconnected".
