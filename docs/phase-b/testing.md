# Testing Guidelines — Phase B: Containerized & Message-Bus Architecture

This document describes the testing requirements, unit tests, and manual verification procedures for the **Phase B: Containerized & Message-Bus Architecture** of the IGNIS system.

---

## Testing Prerequisites

Phase B shifts from a synchronous python execution model to an asynchronous, message-driven, containerized architecture.
- **Unit Testing Prerequisites**: Python 3.10+. Test suites mock `paho-mqtt` sockets, allowing unit tests to run locally on the host machine without requiring a live MQTT broker.
- **Integration Testing Prerequisites**: 
  - Docker Desktop (with Docker Compose v2 support).
  - Web browser access to `http://localhost:8000`.
- **Test Path**: Run all host commands from the root directory.

---

## Unit Testing

The unit tests for this phase are implemented in `tests/test_aggregation.py`. They validate the zone-level aggregation and alert publishing rules.

### Test Cases and Coverage

1. **All Green Aggregation (`test_all_green_aggregation`)**:
   - Simulates telemetry ingestion where three edge nodes (E11, E12, E13) report GREEN status.
   - Verifies that the resulting aggregated zone status is **GREEN**.
   - Confirms that the zone-level WHI matches the maximum WHI among the three nodes.
2. **Maximum State Escalation (`test_max_state_escalation`)**:
   - Simulates a worst-case wildfire event where E12 reports **RED** while E11 and E13 remain **GREEN**.
   - Confirms that the zone state correctly escalates to **RED** (maximum-state aggregation policy, preventing dilution).
   - Verifies that the state transition successfully triggers the publication of a zone state update, a critical regional alert, and presuppression action logs.
3. **Clamping Propagation (`test_clamp_propagation`)**:
   - Simulates an edge node experiencing elevated WHI but clamped to **YELLOW** due to single-sensor isolation (1 confirmation).
   - Confirms that the zone state inherits the **YELLOW** state and propagates the `is_state_clamped: True` tag to inform upstream operators.

### Running the Unit Tests

Execute the unit tests by running the following command from the project root:
```bash
python -m unittest tests/test_aggregation.py
```

---

## Manual Verification Scenarios

Manual verification validates the interactions of edge simulator containers, the Mosquitto MQTT broker, the Fog Node daemon, and the FastAPI local control center dashboard.

### 1. Starting the Simulation Stack
Build and start the services in Docker:
```bash
docker compose up --build
```

### 2. Live Dashboard Baseline Validation
1. Open `http://localhost:8000` in a web browser.
2. Verify that all three edge nodes (E11, E12, E13) and the Simlipal Core Zone (Zone 4B) display **GREEN** status.
3. Observe the live charts. Telemetry values should drift slightly over time due to the baseline `RandomWalkProvider`.

### 3. Interactive Scenario Injections

Use the control dashboard panel to inject the following scenarios:

- **Trigger Scenario S3 (Sudden Ignition)**:
  - Click the **S3** button.
  - **Verification**: The scenario orchestrator publishes sensor overrides over MQTT. Verify that the Fog Node processes the spikes, escalates the zone state immediately to **RED**, and the dashboard log feed records critical presuppression actuations (mist perimeters, control alerts).
- **Trigger Scenario S4 (Single Sensor Fault)**:
  - Click the **S4** button.
  - **Verification**: E12 reports an isolated temperature spike. Verify that the Fog Node clamps the zone state to **YELLOW** (clamped badge active on UI) because only one sensor confirmed the spike, verifying that false-alarm protection is active over MQTT.
