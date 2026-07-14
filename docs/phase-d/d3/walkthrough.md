# Walkthrough — Phase D, Sub-Phase D3: Lateral Pub/Sub & Wind-Bearing Logic

Sub-Phase D3 implements the core lateral communication channel between Fog Nodes, enabling wind-aligned hazard propagation and pre-emptive risk escalation.

---

## Technical Implementations & Codebase Changes

### 1. Fog Node Runner Upgrades
- **[MODIFY] [src/fog_node_runner.py](file:///d:/projects/IGNIS/src/fog_node_runner.py)**:
  - **Subscription**: Subscribed to the lateral coordination wildcard topic (`ignis/v1/fog/zone/+/lateral`) inside `on_connect_cloud`.
  - **Callbacks Routing**: Extended `on_message_cloud` callback to route incoming MQTT packets:
    - Neighbor coordination broadcasts are passed to `_handle_lateral_warning(payload)`.
    - Operator advisory commands are processed via `_handle_advisory_command(payload)`.
    - Added fallback checks checking for payload signatures (`message_type` or `wind_dir_deg`) to support backward-compatibility and unit tests where mock messages omit the `topic` attribute.
  - **Wind Alignment Logic**: Implemented `check_wind_alignment(wind_deg, target_bearing, tolerance)` to evaluate if the wind direction falls within the ±tolerance cone of a neighbor's bearing.
  - **Vector Wind Averaging**: Implemented `compute_vector_wind_average(readings)` to average wind bearings using trigonometry (vector sine/cosine sums), ensuring that headings like 350° and 10° average to 0°/360° instead of 180°. Added automatic normalization of `360.0` degrees back to `0.0` degrees.
  - **Pre-emptive Escalation**:
    - Periodically expires lateral warnings older than the timeout limit (`lateral_warning_timeout_sec`).
    - If there are active, wind-aligned warnings from neighbors and the local zone's raw sensor state is `GREEN`, the zone state escalates pre-emptively to `YELLOW`.
  - **Lateral Broadcasts**: Added `_publish_lateral_broadcast(...)` which publishes the current state, hazard index, and averaged wind vector to `ignis/v1/fog/zone/{zone_id}/lateral` on state transitions to `YELLOW` or higher.

---

## Verification & Validation Results

### Unit Test Suite
Verified the circular vector wind averaging, angular tolerance, wind alignment, own-broadcast filtering, and pre-emptive yellow escalation under aligned wind conditions.

#### Running the Test Suite:
```bash
python -m unittest discover tests
```

#### Test Execution Output:
```text
Ran 25 tests in 0.030s

OK
```
All tests passed successfully, confirming lateral warnings propagation and safety gates behavior.
