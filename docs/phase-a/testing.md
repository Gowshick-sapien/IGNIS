# Testing Guidelines — Phase A: Core Decision Pipeline

This document describes the testing requirements, unit tests, and manual verification procedures for the **Phase A: Core Decision Pipeline** of the IGNIS wildfire early warning system.

---

## Testing Prerequisites

Phase A focuses on the local mathematical scoring engine and state machine.
- **Runtime Environment**: Python 3.10+
- **External Dependencies**: None. All core calculations and tests are written using standard library components (e.g. `unittest`).
- **Test Path**: All test execution commands should be run from the repository root directory.

---

## Unit Testing

The unit tests for this phase are implemented in `tests/test_scoring.py`. They validate each module of the wild fire scoring pipeline independently.

### Test Cases and Coverage

1. **Sensor Normalization Bounds (`test_normalization_bounds`)**:
   - Verifies that raw sensor readings are correctly scaled between `0.0` and `1.0`.
   - Confirms that input values exceeding the min/max limits are clamped.
   - Validates that inverted parameters (e.g. humidity and soil moisture, where lower values represent higher risk) are correctly inverted.
2. **Time of Day Normalization (`test_time_of_day_normalization`)**:
   - Assures that diurnal risk peaks at `14:00` (1.0 risk multiplier) and hits its lowest point at `02:00` (0.0 multiplier) following a custom solar radiation curve.
3. **Wildfire Hazard Index (WHI) Computation (`test_hazard_index_computation`)**:
   - Validates the mathematical weight-accumulation formula. Confirms that if all normalized sensor fields are `0.5`, the resulting WHI equals `0.5` (given weights sum to `1.0`).
4. **Sensor Confirmation Count (`test_confirmations_count`)**:
   - Validates the confirmation logic used to filter faulty sensor spikes.
   - Verifies that only sensors that meet or exceed their preconfigured activation thresholds contribute to the confirmation count.
5. **State Machine Clamping (`test_state_machine_clamping`)**:
   - **Case A**: Tests that if WHI is high (`0.85`) but the sensor confirmation count is less than `3` (e.g., only 2 sensors crossed their thresholds), the final hazard state is clamped to **YELLOW** to prevent single-sensor false alarms.
   - **Case B**: Tests that if WHI is high (`0.85`) and at least `3` independent sensors confirm the hazard, the state machine successfully escalates to **RED**.

### Running the Unit Tests

Execute the unit tests by running the following command from the project root:
```bash
python -m unittest tests/test_scoring.py
```

---

## Manual Verification Scenarios

Manual verification in Phase A executes simulated environmental conditions step-by-step through a console runner.

### Running the Scenario Simulator

Execute the simulation suite using:
```bash
python run_phase_a.py
```

### Scenario Test Matrix and Expected Behaviors

| Scenario | Objective | Input Behavior | Expected Output Behavior |
|----------|-----------|----------------|--------------------------|
| **S1: Normal Day** | Verify system baseline stability | Telemetry drifts slightly within baseline ranges. | State remains **GREEN** throughout. WHI remains low (< 0.20). No actions are triggered. |
| **S2: Slow-Building Risk** | Verify gradual risk build-up | Telemetry elements (temperature, gas) slowly rise. | State transitions from **GREEN** -> **YELLOW**. As risk escalates and 3 sensors confirm, it transitions to **ORANGE** and logs perimeter mist activation. |
| **S3: Sudden Ignition** | Verify instant emergency trigger | Telemetry values for temperature, gas, and thermal anomalies spike instantly. | State transitions directly to **RED** in step 1. Logs maximum presuppression actuation and control alerts. |
| **S4: Single Sensor Fault** | Verify false-positive mitigation | A single temperature sensor is forced to a high fault value (e.g., 45.0°C) while other sensors remain normal. | WHI calculation increases, but state is clamped to **YELLOW** because the confirmation count is 1. No critical actions (ORANGE/RED) are logged. |
