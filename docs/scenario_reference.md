# IGNIS -- Scenario Validation Reference

This document describes the seven standardized test scenarios (S1-S7) that constitute the IGNIS V1 validation suite. Each scenario exercises a specific set of architectural capability claims and is defined as a versioned, schema-validated YAML configuration file in `scenarios/`.

---

## 1. Scenario Suite Overview

| ID | Name | Target Capability | Expected Final State | Key Metric Target |
| :--- | :--- | :--- | :--- | :--- |
| S1 | Normal Day | Baseline stability | GREEN | 0.0% false positive rate |
| S2 | Slow-Building Risk | Gradual escalation detection | YELLOW | 0.0% false positive rate |
| S3 | Sudden Ignition | Rapid multi-sensor threat response | RED | Fog decision latency under 150 ms |
| S4 | Single Sensor Fault | False positive suppression (clamping) | YELLOW (clamped) | 0 false positive escalations |
| S5 | Cloud Outage | Offline resilience and data continuity | RED | 100% buffered event flush on reconnect |
| S6 | Lateral Spread | Peer-to-peer predictive alerting | RED | Lateral propagation under 5.0 s |
| S7 | Multi-Zone Concurrent | Cross-zone isolation under load | RED | 0 crosstalk messages, 0% message loss |

---

## 2. Scenario Descriptions

### S1 -- Normal Day

**File:** `scenarios/s1_normal.yaml`

**Purpose:** Verify that the system maintains GREEN state under benign environmental conditions. All sensor readings remain within safe bounds across all 6 steps. No escalation should occur.

**Sensor Trajectory:** Gentle diurnal drift. Temperature ranges from 28.0 to 30.0 deg C, humidity holds at 52-55%, wind at 6-7.5 km/h, soil moisture at 27-28%, gas at 12.0-12.5 ppm, thermal anomaly at 0.2-0.45 deg C. Seasonal baseline: 0.3 (low risk season).

**Expected Outcome:**
- Final state: GREEN
- Maximum state reached: GREEN
- Clamped: No
- False positive rate: 0.0%

**Validation Assertions:**
- `max_state == GREEN`

**Capability Validated:** System does not generate false alerts during routine environmental conditions.

---

### S2 -- Slow-Building Risk

**File:** `scenarios/s2_slow_risk.yaml`

**Purpose:** Verify that the system correctly detects a gradual multi-parameter drift toward dangerous conditions and escalates from GREEN to YELLOW. The drift should NOT reach ORANGE because insufficient sensors cross their confirmation thresholds simultaneously.

**Sensor Trajectory:** Temperature rises from 30.0 to 37.5 deg C over 6 steps. Humidity drops from 45% to 28.5%. Soil moisture drops from 26% to 16.5%. Wind increases from 8 to 15.8 km/h. Gas rises slightly from 14.0 to 18.3 ppm. Thermal anomaly drifts from 0.5 to 1.6 deg C. Seasonal baseline: 0.8 (high risk season).

**Expected Outcome:**
- Final state: YELLOW
- Maximum state allowed: YELLOW
- Clamped: No
- False positive rate: 0.0%

**Validation Assertions:**
- `max_state <= YELLOW`

**Capability Validated:** WHI correctly transitions through GREEN to YELLOW on gradual parameter degradation. The system does not over-escalate when confirmation counts are insufficient.

---

### S3 -- Sudden Ignition

**File:** `scenarios/s3_sudden_ignition.yaml`

**Purpose:** Verify that a sudden multi-sensor fire event triggers rapid escalation through ORANGE to RED with autonomous action logging. This is the primary latency benchmark scenario.

**Sensor Trajectory:** Starts with normal readings (temperature 32 deg C, humidity 40%, gas 12 ppm). At step 3, a sudden ignition event occurs: temperature spikes to 44.0 deg C, humidity crashes to 18%, wind gusts to 32 km/h, soil moisture drops to 6%, gas surges to 85 ppm, thermal anomaly jumps to 9.0 deg C. Seasonal baseline: 0.85.

**Target Mode:** Localized (affects node index 1 in Zone 4B, i.e., 4B-E2).

**Expected Outcome:**
- Final state: RED
- Maximum state allowed: RED
- Clamped: No
- Fog decision latency target: under 1.0 s (YAML assertion threshold: 5.0 s; benchmark target: under 150 ms)

**Validation Assertions:**
- `fog_decision_latency <= 5.0 seconds`
- `final_state == RED`

**Capability Validated:** Sub-second autonomous threat detection and action triggering. Measures the critical fog decision latency metric.

---

### S4 -- Single Sensor Fault

**File:** `scenarios/s4_sensor_fault.yaml`

**Purpose:** Verify that a single malfunctioning sensor cannot escalate the system past YELLOW, even if the faulty readings drive the WHI above the ORANGE threshold. This validates the multi-sensor confirmation clamping rule.

**Sensor Trajectory:** Starts with slightly elevated but sub-threshold readings. At step 3, the gas sensor spikes to 100 ppm (maximum) while all other sensors remain at moderate, non-confirming levels (temperature 38 deg C -- below the 40 deg C confirmation threshold, humidity 30% -- above the 25% confirmation threshold, etc.). The WHI rises due to the extreme gas reading, but fewer than 3 sensors cross their confirmation thresholds.

**Target Mode:** Localized (affects node index 1 in Zone 4B).

**Expected Outcome:**
- Final state: YELLOW
- Maximum state allowed: YELLOW
- Clamped: Yes (Single Fault Guard activated)
- False positive count: 0

**Validation Assertions:**
- `false_positive_count == 0`
- `is_clamped == true`

**Capability Validated:** Multi-sensor confirmation rule prevents false ORANGE/RED escalation from isolated sensor anomalies.

---

### S5 -- Cloud Outage

**File:** `scenarios/s5_cloud_outage.yaml`

**Purpose:** Verify that the fog node continues all local operations (scoring, state evaluation, action logging) during a cloud WAN disconnection, and that buffered events are flushed with 100% data continuity upon reconnection.

**Sensor Trajectory:** Similar ignition profile to S3 (sudden fire event). A chaos action disconnects the cloud broker at t+8s for 20 seconds. The fire event occurs during the disconnection period, forcing the fog node to operate autonomously.

**Chaos Actions:**
- `disconnect_cloud` at time offset 8s, duration 20s

**Expected Outcome:**
- Final state: RED
- Maximum state allowed: RED
- Clamped: No
- Offline continuity: true (fog continued operating during outage)
- Flush success rate: 1.0 (100% of buffered events recovered)

**Validation Assertions:**
- `offline_continuity == true`
- `flush_success_rate == 1.0`

**Capability Validated:** Fog-level decision autonomy persists through WAN partitions. BufferedPublisher correctly queues and flushes all events.

---

### S6 -- Lateral Spread

**File:** `scenarios/s6_lateral_spread.yaml`

**Purpose:** Verify that when Zone 4B detects a fire event with wind blowing toward Zone 4C (southward, 180 deg), Zone 4C receives the lateral warning and pre-emptively escalates its own state before its own sensors detect any anomaly.

**Sensor Trajectory:** Zone 4B experiences a fire event (similar to S3) with wind direction set to 180 deg (south). Zone 4C sensors remain at baseline safe levels. The lateral warning from 4B should cause 4C to escalate from GREEN to YELLOW pre-emptively.

**Expected Outcome:**
- Final state (Zone 4B): RED
- Maximum state allowed: RED
- Clamped: No
- Lateral propagation time target: under 10.0 s (YAML assertion; benchmark target: under 5.0 s)

**Validation Assertions:**
- `lateral_propagation_time <= 10.0 seconds`

**Capability Validated:** Peer-to-peer fog coordination enables predictive fire spread alerting based on wind vector alignment.

---

### S7 -- Multi-Zone Concurrent

**File:** `scenarios/s7_multi_zone.yaml`

**Purpose:** Verify that simultaneous fire events across multiple zones (4A, 4B, 4C) produce no dropped messages, no cross-zone data leakage, and correct independent state evaluation in each zone.

**Sensor Trajectory:** Simultaneous ignition events across all three zones. Each zone's edge nodes experience fire-level sensor spikes independently.

**Expected Outcome:**
- Final state: RED (in all zones)
- Maximum state allowed: RED
- Clamped: No
- Cross-talk count: 0 (no messages leaked between isolated zone brokers)
- Message loss: 0.0%

**Validation Assertions:**
- `cross_talk_count == 0`
- `message_loss_pct == 0.0`

**Capability Validated:** MQTT broker isolation ensures zone-level message integrity under concurrent multi-zone load.

---

## 3. YAML Schema Structure

Every scenario YAML file follows a standardized schema enforced by `src/scenarios/yaml_validator.py`:

```yaml
scenario_id: "S1"                          # Unique scenario identifier
description: "..."                         # Human-readable description
version: "1.0"                             # Schema version

target:
  mode: "global" | "localized"             # Whether all nodes or a specific node is affected
  zone_ids: ["4B"]                         # Target zone(s)
  target_node_index: 1                     # (localized mode only) Index of target edge node

steps:
  - index: 0                               # Step sequence number (0-based)
    duration_sec: 4                        # Duration of this step in seconds
    sensor_data:
      temperature_c: 28.0                  # All 9 sensor parameters
      humidity_pct: 55.0
      wind_speed_kmh: 6.0
      wind_dir_deg: 180.0
      soil_moisture_pct: 28.0
      gas_ppm: 12.0
      thermal_anomaly_c: 0.2
      light_lux: 20000.0
      rain_mm: 0.0
    seasonal_baseline: 0.3                 # Seasonal drought risk factor

chaos_actions:                             # Fault injection actions (can be empty)
  - type: "disconnect_cloud"
    time_offset_sec: 8
    duration_sec: 20

expected_outcome:
  final_state: "GREEN"                     # Expected final zone state
  max_state_allowed: "GREEN"               # Maximum permitted state (for validation)
  is_clamped: false                        # Whether clamping should be active

metrics_targets:                           # Benchmark metric targets
  false_positive_rate: 0.0
  fog_decision_latency: 1.0

validation:
  require_events: true
  min_event_count: 1
  timeout_sec: 60
  assertions:                              # Machine-verifiable assertions
    - metric: "max_state"
      operator: "=="
      threshold: "GREEN"
      unit: "state"

metadata:
  forest_type: "dry_deciduous"             # Ecological context tag
  zone_profile: "simlipal_core"            # Zone profile tag
```

---

## 4. Benchmark Performance Results (N=30 Trials)

| Scenario | Primary Metric | Target | Measured | Verdict |
| :--- | :--- | :--- | :--- | :---: |
| S1 | Max state reached | GREEN | GREEN (30/30) | PASS |
| S2 | Max state reached | YELLOW | YELLOW (30/30) | PASS |
| S3 | Fog decision latency | under 150 ms | 88.4 ms +/- 4.2 ms | PASS |
| S4 | False positive count | 0 | 0 (30/30), clamped | PASS |
| S5 | Buffered event flush rate | 100% | 100% (30/30) | PASS |
| S6 | Lateral propagation time | under 5.0 s | 3.24 s +/- 0.18 s | PASS |
| S7 | Crosstalk messages | 0 | 0 (30/30) | PASS |

---

## 5. Running Scenarios

### Via Experiment Orchestrator (CLI)

```bash
# Run all 7 scenarios with 10 trials each
python -m src.run_experiment --trials 10 --clean

# Run specific scenarios
python -m src.run_experiment --trials 5 --scenarios S1 S3 S4
```

### Via Dashboard UI

Navigate to the **Experiment Control Center** at `/experiments`. Select scenarios, configure trial count and seed, and execute with live SSE progress streaming.

### Via NOC Simulation Drawer

Navigate to the **Regional Operations NOC** at `/`. Use the collapsible simulation drawer to inject individual scenarios (S1-S4, S6) into specific zones with live step-by-step progress visualization.
