# Implementation Plan - IGNIS Simulation Phase A

This plan outlines the design and implementation of **Phase A (Core Pipeline)** for the IGNIS (Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance) software simulation, based on the `Simulation_Ideation_v1` and `hardware_ideation_v1` documents.

Phase A establishes a single edge node -> single fog node local pipeline using direct function calls, validating the data model, risk-scoring logic, and the multi-sensor confirmation rules without external dependencies like Docker or MQTT.

---

## User Review Required

> [!IMPORTANT]
> The risk-scoring and state classification thresholds are configured dynamically through a JSON file, allowing customization per forest zone without modifying code.

> [!IMPORTANT]
> **Multi-Sensor Confirmation Rule (Section 8.4)**: To prevent false positives, we enforce that even if the aggregate risk score exceeds the `ORANGE` or `RED` threshold, the system will not transition to `ORANGE` or `RED` unless at least **three** independent sensor parameters have crossed their respective confirmation thresholds. If they do not, the state will be clamped to `YELLOW` (or remain `GREEN`).

---

## Proposed Changes

We will organize the code under the project root (`d:\projects\IGNIS`) in a structured Python package.

### Configuration

#### [NEW] [zone_config.json](file:///d:/projects/IGNIS/config/zone_config.json)
Contains weights, normalization boundaries, individual confirmation thresholds for each sensor parameter, and state transition thresholds for a specific forest division (e.g., zone "4B").

### Source Code

#### [NEW] [edge_node.py](file:///d:/projects/IGNIS/src/edge_node.py)
Implements the `EdgeNode` class representing a sensor cluster.
- Generates synthetic sensor readings for: temperature, humidity, wind speed, wind direction, soil moisture, gas/smoke level, thermal anomaly, light intensity, rainfall, and GPS coordinates.
- Supports three data generation modes:
  - **Baseline**: Natural drift with random walks within seasonal normal ranges.
  - **Scenario-driven**: Emits exact predetermined values from a test script to simulate specific sequences.
  - **Fault**: Simulates faulty sensor behavior (e.g., stuck values, extreme out-of-range readings).

#### [NEW] [fog_node.py](file:///d:/projects/IGNIS/src/fog_node.py)
Implements the `FogNode` class representing the "local brain".
- Ingests readings from edge nodes.
- Normalizes each sensor reading to a value in $[0.0, 1.0]$ using configuration boundaries:
  - Higher temperature, lower humidity, higher wind speed, lower soil moisture, higher gas levels, and higher thermal anomaly contribute to higher risk.
  - Time of day is normalized using a peak at 14:00 (2 PM) as the highest risk hour.
  - Seasonal baseline is supplied directly from config.
- Computes aggregate `risk_score` as a weighted sum of normalized values.
- Performs state classification (`GREEN`, `YELLOW`, `ORANGE`, `RED`).
- Enforces the **Multi-Sensor Confirmation Rule**:
  - Evaluates individual confirmation conditions:
    1. Temperature $\ge$ threshold
    2. Humidity $\le$ threshold
    3. Wind Speed $\ge$ threshold
    4. Soil Moisture $\le$ threshold
    5. Gas Level $\ge$ threshold
    6. Thermal Anomaly $\ge$ threshold
  - If the computed state is `ORANGE` or `RED`, but the number of crossed confirmation thresholds is $< 3$, the state is clamped to `YELLOW`.
- Emits structured decision records and logs simulated autonomous actions (e.g. `activate_mist_perimeter`, `notify_control_center`).

#### [NEW] [pipeline.py](file:///d:/projects/IGNIS/src/pipeline.py)
A helper file that ties the `EdgeNode` and `FogNode` together and prints clean, formatted console summaries of the simulation execution.

### Demonstration and Runner

#### [NEW] [run_phase_a.py](file:///d:/projects/IGNIS/run_phase_a.py)
The entry point script that plays back four scenarios representing the core test cases:
1. **Scenario S1: Normal Day** (Baseline drift, stays `GREEN`).
2. **Scenario S2: Slow-Building Risk** (Gradual drift, transitions to `YELLOW`).
3. **Scenario S3: Sudden Ignition** (Rapid spike in multiple sensors, escalates to `RED` as confirmation rule is met).
4. **Scenario S4: Single Sensor Fault** (Extreme spike in gas sensor only; risk score increases but is clamped to `YELLOW` because confirmation count is 1).

---

## Verification Plan

We will verify Phase A by running the simulation pipeline program and reviewing the console logs.

### Manual Verification
- Run `run_phase_a.py` and inspect the formatted console output:
  - Verify that Scenario S1 stays `GREEN`.
  - Verify that Scenario S2 transitions to `YELLOW` as parameters drift.
  - Verify that Scenario S3 successfully reaches `RED` when temperature, gas, thermal anomaly, and humidity spike.
  - Verify that Scenario S4 remains `YELLOW` (or `GREEN`) despite a high gas reading, showing the confirmation rule clamped the alert.
- Run automated unit tests to verify the correctness of the risk calculation and the confirmation clamping logic.

####################################################################\

# Implementation Plan - IGNIS Simulation Phase A (Updated)

This plan outlines the design and implementation of **Phase A (Core Pipeline)** for the IGNIS software simulation, incorporating feedback to refine architecture modularity, decoupling, and terminology.

Phase A establishes a single edge node -> single fog node local pipeline using direct function calls, validating the data model, scoring logic, and the state transitions.

---

## User Review Required

> [!IMPORTANT]
> **Key Refinements Integrated**:
> 1. **Terminology**: `risk_score` is renamed to **Wildfire Hazard Index (WHI)**.
> 2. **State Machine Decoupling**: The state machine takes both the WHI and the sensor confirmation count as distinct inputs, rather than making the state machine implicitly nested within a single score computation.
> 3. **Edge Node Decoupling**: The `EdgeNode` represents a simple sensor cluster interface. Scenario generation (e.g., normal day drift, sudden ignition trajectories) is factored out into a dedicated `ScenarioGenerator` module to facilitate future transition to MQTT/hardware.
> 4. **Modular Scoring Logic**: The scoring and classification pipeline is organized into independent helper modules (`normalization`, `hazard_index`, `confirmation`, and `state_machine`) under a `scoring` package.
> 5. **Separation of Presentation**: The pipeline execution is purely functional and returns structured JSON-like dictionaries. A separate presentation module formatting the logs is used for console representation.

---

## Proposed Changes

We will organize the code under the project root (`d:\projects\IGNIS`) in a structured Python package.

### Configuration

#### [NEW] [zone_config.json](file:///d:/projects/IGNIS/config/zone_config.json)
Defines parameters for a forest division (e.g., zone "4B"):
- Weights for WHI calculation.
- Normalization ranges for sensors (min, max).
- Individual sensor confirmation thresholds.
- State transition boundaries (WHI thresholds for GREEN, YELLOW, ORANGE, RED).

### Scoring Logic Modules (`src/scoring/`)

#### [NEW] [__init__.py](file:///d:/projects/IGNIS/src/scoring/__init__.py)
Exposes the core scoring interfaces.

#### [NEW] [normalization.py](file:///d:/projects/IGNIS/src/scoring/normalization.py)
Normalizes raw sensor parameters (temperature, humidity, wind speed, soil moisture, gas, thermal anomaly, time of day) to $[0.0, 1.0]$.
- Peak temperature, wind speed, gas levels, and thermal anomalies scale risk upward.
- Soil moisture and relative humidity scale risk downward (i.e. dry conditions contribute to higher risk).
- Time of day is normalized using a peak at 14:00 (2 PM) as the highest risk hour.

#### [NEW] [hazard_index.py](file:///d:/projects/IGNIS/src/scoring/hazard_index.py)
Computes the **Wildfire Hazard Index (WHI)** as a weighted sum of the normalized parameters based on the weights configuration.

#### [NEW] [confirmation.py](file:///d:/projects/IGNIS/src/scoring/confirmation.py)
Evaluates raw sensor readings against their confirmation thresholds.
- Returns a list of sensors that have crossed their thresholds (e.g., `['gas_ppm', 'thermal_anomaly_c']`) and the confirmation count (length of the list).

#### [NEW] [state_machine.py](file:///d:/projects/IGNIS/src/scoring/state_machine.py)
Maps the WHI and confirmation count to a risk state (`GREEN`, `YELLOW`, `ORANGE`, `RED`).
- State machine rules:
  - If WHI $\ge$ RED threshold and confirmation count $\ge$ 3 $\rightarrow$ `RED`
  - If WHI $\ge$ ORANGE threshold and confirmation count $\ge$ 3 $\rightarrow$ `ORANGE`
  - If WHI $\ge$ YELLOW threshold $\rightarrow$ `YELLOW`
  - Else $\rightarrow$ `GREEN`
  - Clamping behavior: If the WHI is high enough for ORANGE/RED, but confirmation count is $< 3$, the state is clamped to `YELLOW` to control false positives.

### Core Architecture (`src/`)

#### [NEW] [edge_node.py](file:///d:/projects/IGNIS/src/edge_node.py)
Implements `EdgeNode` representing a physical sensor cluster.
- Exposes a clean interface: `get_reading(sensor_data)` or similar, which formats and returns structured JSON-like readings with appropriate node metadata (ID, zone, timestamp).
- Contains no scenario simulation logic itself.

#### [NEW] [fog_node.py](file:///d:/projects/IGNIS/src/fog_node.py)
Implements `FogNode` representing the "local brain".
- Coordinates the ingestion and execution of the scoring logic:
  1. Calls `normalization` on incoming edge readings.
  2. Calls `hazard_index` to compute the WHI.
  3. Calls `confirmation` to assess individual threshold crossings.
  4. Calls `state_machine` to evaluate the risk state.
  5. Determines autonomous actions (e.g. `activate_mist_perimeter`) based on the state.
- Returns structured decision records without doing console logging directly.

### Scenarios & Presentation

#### [NEW] [scenario.py](file:///d:/projects/IGNIS/src/scenario.py)
Implements `ScenarioGenerator` which creates environmental trajectories (data series) for tests.
- Provides functions for:
  - Normal Day (S1)
  - Slow-Building Risk (S2)
  - Sudden Ignition (S3)
  - Single Sensor Fault (S4)
- Feeds data directly to the pipeline.

#### [NEW] [presenter.py](file:///d:/projects/IGNIS/src/presenter.py)
Formats and prints structured decision records and action logs to the console using clean, high-visibility styling.

### Runner

#### [NEW] [run_phase_a.py](file:///d:/projects/IGNIS/run_phase_a.py)
The entry point script orchestrating the simulation:
- Loads the zone configuration.
- Instantiates `EdgeNode` and `FogNode`.
- Uses `ScenarioGenerator` to feed trajectories into the node pipeline.
- Passes decision records to `Presenter` to output results to the console.

---

## Verification Plan

### Automated Tests
- Test cases inside `tests/` verifying normalization, WHI weights, the confirmation counts, and state machine clamping rules.

### Manual Verification
- Execute `python run_phase_a.py` and inspect the formatted console output to confirm expected states:
  - S1: Normal Day $\rightarrow$ Stays `GREEN`
  - S2: Slow-Building Risk $\rightarrow$ Transitions to `YELLOW`
  - S3: Sudden Ignition $\rightarrow$ Reaches `RED`
  - S4: Single Sensor Fault $\rightarrow$ Clamped to `YELLOW`
