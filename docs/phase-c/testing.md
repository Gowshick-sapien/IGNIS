# Testing Guidelines — Phase C: Centralized Cloud Layer

This document describes the testing requirements, unit tests, and manual verification procedures for the **Phase C: Centralized Cloud Layer** of the IGNIS system.

---

## Testing Prerequisites

Phase C adds centralized logging (InfluxDB v2), an independent ingestor worker, a stateless NOC dashboard, and robust advisory command verification.
- **Unit Testing Prerequisites**: Python 3.10+. Libraries `paho-mqtt`, `influxdb-client`, and `python-dotenv` are mocked, allowing tests to run locally on the host python interpreter.
- **Integration Testing Prerequisites**:
  - Docker Desktop (with Docker Compose v2).
  - Web browser access to both the local dashboard (`http://localhost:8000`) and the NOC central dashboard (`http://localhost:9000`).
- **Test Path**: Run all host commands from the root directory.

---

## Unit & Resilience Testing

The unit tests for this phase are implemented in `tests/test_cloud_resilience.py`. They validate the ingestor buffering logic and the fog runner advisory security gates.

### Test Cases and Coverage

1. **Advisory Command Verification (`test_advisory_command_valid`)**:
   - Sends a valid state override command (`RED`) to the Fog Node.
   - Verifies that the Fog Node intercepts it, applies the state clamp, triggers presuppression actions, and publishes a `SUCCESS` response.
2. **Duplicate Command Rejection (`test_advisory_command_duplicate_rejected`)**:
   - Injects a command payload with a duplicate UUID `command_id` that was already processed.
   - Verifies that the Fog Node Runner rejects it immediately, logs a `FAILED` response, and does not apply the override parameters.
3. **Expired Command Rejection (`test_advisory_command_expired_rejected`)**:
   - Injects a command with a timestamp older than the configuration `ttl` limit (e.g. 1 hour old).
   - Verifies that the replay protection gate filters it out, registers `FAILED`, and ignores the command.
4. **Database Offline Buffering & Recovery (`test_ingestor_offline_buffering_and_flush`)**:
   - Simulates database connectivity loss (`ping() -> False`).
   - Ingests telemetry and latency records. Verifies that the ingestor service buffers them in a local in-memory array (`offline_buffer`) without crashing.
   - Simulates database recovery (`ping() -> True`) and triggers a flush. Confirms that all buffered records are written to InfluxDB and the queue is cleared.

### Running the Unit Tests

Execute the unit tests by running:
```bash
python -m unittest tests/test_cloud_resilience.py
```
To run all tests in the repository together:
```bash
python -m unittest discover tests
```

---

## Manual Verification Scenarios

Manual verification validates the central cloud layer, database persistent schema, stateless NOC UI dashboard, and the bidirectional command routing.

### 1. Starting the Stack
Launch the environment in Docker:
```bash
docker compose up --build
```
Ensure both dashboards are accessible:
- Local Control Center: `http://localhost:8000`
- Central NOC Dashboard: `http://localhost:9000`

### 2. Manual Scenarios Verification

#### Scenario S8 — Cloud Advisory Override
1. Open the Central Dashboard at `http://localhost:9000`.
2. Locate the **Operator Advisory Console** in the left panel.
3. Select Zone `4B`, choose **RED (Emergency Actuate)**, and click **Clamp**.
4. **Verification**: 
   - Check that the Audit table on the right side displays the command state transition: `PENDING` -> `SUCCESS`.
   - Verify that the local `FogNode` adopts the RED state immediately, triggers perimeter mist and emergency notifications, and logs it.
   - Access `http://localhost:8000`. Verify that the local dashboard displays RED with the central override badge active.
5. Click **Release State Override** on the central dashboard. Confirm the system returns to automatic telemetry-driven calculation.

#### Scenario S9 — Dynamic Threshold Policy Adjustment
1. Select Zone `4B` on the central dashboard and increase the temperature activation threshold to `50.0°C` in the Policy Adjustment panel.
2. Click **Set**. Verify the audit trail confirms execution success.
3. On the local control center dashboard (`http://localhost:8000`), trigger Scenario **S3 (Sudden Ignition)**.
4. Inject a telemetry tick with temperature `45.0°C` (which previously triggered RED).
5. **Verification**: Confirm that the Fog Node remains in a GREEN/YELLOW warning state because the temperature does not cross the new `50.0°C` policy limit, verifying that policy rules update dynamically.

### 3. Database Offline Resilience Verification
1. With the stack running and active edge telemetry flowing, stop the InfluxDB database container:
   ```bash
   docker stop ignis-influxdb
   ```
2. Verify that the Central Dashboard shows InfluxDB as `OFFLINE` in the topology grid.
3. Let the edge simulation continue running for 30–60 seconds. Inspect the ingestor service logs to verify it continues receiving MQTT ticks and buffers them in memory:
   ```bash
   docker logs ignis-cloud-ingestor
   ```
4. Start InfluxDB back up:
   ```bash
   docker start ignis-influxdb
   ```
5. **Verification**: Verify that the ingestor detects database recovery, flushes all buffered points, and the dashboard charts fill up with no telemetry data gaps.
