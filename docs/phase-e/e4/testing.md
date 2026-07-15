# Phase E4 Testing: Chaos Controller Service

This document outlines the testing strategy, test cases, and execution procedures for Phase E4 (Chaos Controller Service).

## Test Strategy

Since unit tests execute in environments without Docker or active container runtimes, we decouple the API routes and Adapter methods from physical Docker daemons. We test the API endpoints and the `DockerAdapter` logic by injecting mocked Docker clients and checking correct SDK invocations.

Dependencies:
- `docker` (Python SDK).
- `httpx` (Required by FastAPI TestClient).

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Routes Endpoints Verification (`test_routes_endpoints`)
- **Objective**: Verify that FastAPI REST endpoints validate payloads, return correct JSON responses, and trigger adapter operations.
- **Procedure**:
  1. Patch the `adapter` instance inside `routes.py` with a `MagicMock`.
  2. Launch a FastAPI `TestClient` pointing to the main `app`.
  3. Send request payloads for:
     - `GET /api/chaos/status`
     - `POST /api/chaos/disconnect_cloud`
     - `POST /api/chaos/restore_cloud`
     - `POST /api/chaos/kill_container`
     - `POST /api/chaos/restart_container`
  4. Assert that each endpoint returns HTTP status `200 OK`.
  5. Assert that request parameters map to the correct mock adapter methods.

### 2. Docker Adapter Methods (`test_docker_adapter_methods`)
- **Objective**: Verify that `DockerAdapter` invokes the appropriate container and network commands against the Docker client.
- **Procedure**:
  1. Instantiate `DockerAdapter` with a mocked Docker client, container, and network.
  2. Invoke `disconnect()` and verify that network disconnection matches container parameters.
  3. Invoke `reconnect()` and verify network connection is made.
  4. Invoke `kill()` and verify that container `.stop()` is called.
  5. Invoke `restart()` and verify container `.restart()` is called.
  6. Invoke `get_status()` and assert container state is parsed correctly.

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
