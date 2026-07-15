# Testing Guidelines — Phase D, Sub-Phase D3: Lateral Pub/Sub & Wind-Bearing Logic

This document describes the testing requirements, unit tests, and verification procedures for **Phase D, Sub-Phase D3 (Lateral Pub/Sub & Wind-Bearing Logic)** of the IGNIS system.

---

## Testing Prerequisites
- **Python Version**: Python 3.10+.
- **Mock libraries**: Unit tests mock `paho-mqtt` client connections, allowing execution on host python environments.

---

## Automated Unit Testing

The unit tests for this sub-phase are located in `tests/test_lateral_coordination.py`.

### Test Cases and Coverage

1. **Direct Hit Angle Checking (`test_wind_alignment_direct_hit`)**:
   - Asserts `check_wind_alignment(180, 180, 45)` returns `True` when wind points directly at the neighbor bearing.
2. **Cone Tolerance (`test_wind_alignment_within_tolerance` & `test_wind_alignment_outside_tolerance`)**:
   - Asserts wind bearings within the angle range (e.g. 200° or 150° for 180° ± 45°) align successfully.
   - Asserts wind bearings outside the range (e.g. 230° or 130° for 180° ± 45°) do not align.
3. **Wraparound Cone Checking (`test_wind_alignment_wraparound` & `test_wind_alignment_wraparound_miss`)**:
   - Validates wraparound cone logic across the 0°/360° boundary (e.g. wind 350° and target bearing 10° with a 30° tolerance checks successfully as `True`).
4. **Vector Wind Averaging (`test_vector_wind_avg_normal` & `test_vector_wind_avg_wraparound`)**:
   - Validates that simple arithmetic averages are avoided: [350°, 10°] correct vector average is `0°`/`360°` rather than `180°`.
5. **Lateral Warning Pre-emptive Escalation (`test_lateral_warning_triggers_preemptive`)**:
   - Validates that when a downwind neighbor publishes a `RED` alert, the node registers the warning, escalates its local state from `GREEN` to `YELLOW`, sets `preemptive_escalation` to `True`, and appends the source neighbor to `lateral_warning_sources`.
6. **Relevance Filtering (`test_lateral_warning_ignored_wrong_bearing`)**:
   - Confirms that if a neighbor publishes a `RED` warning but the wind is blowing away from the local node (wrong bearing), the warning is ignored.
7. **Timeout and Cleanup (`test_lateral_warning_expiry`)**:
   - Verifies that warnings older than `lateral_warning_timeout_sec` are automatically purged during the evaluation loop, resetting the node to `GREEN`.
8. **Feedback Loop Protection (`test_own_broadcast_ignored` & `test_own_broadcast_ignored`)**:
   - Confirms that fog nodes ignore lateral coordination messages matching their own `zone_id`.

### Running the Unit Tests

Run the lateral coordination tests specifically:
```bash
python -m unittest tests/test_lateral_coordination.py
```

Run the entire test suite:
```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 25 tests in 0.030s

OK
```
