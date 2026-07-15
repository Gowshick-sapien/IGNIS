# Walkthrough — Phase D, Sub-Phase D5: Scenario S6 & Test Suite

Sub-Phase D5 implements the multi-zone lateral spread scenario S6 and integrates it into the local Control Center interface, along with automated test coverage for the generation steps.

---

## Technical Implementations & Codebase Changes

### 1. Scenario Generator
- **[MODIFY] [src/scenario.py](file:///d:/projects/IGNIS/src/scenario.py)**:
  - Created `get_lateral_spread_scenario()` generating a 6-step time-series override script.
  - Steps 0–1 model baseline GREEN readings with a wind bearing of 180.0° (blowing south).
  - Steps 2–3 escalate to YELLOW/ORANGE.
  - Steps 4–5 reach full fire (RED). Wind remains at 180.0° throughout.

### 2. Control Center Scenario Service
- **[MODIFY] [src/control_center/scenario_service.py](file:///d:/projects/IGNIS/src/control_center/scenario_service.py)**:
  - Upgraded `__init__` to select the list of active simulator node IDs dynamically based on the current `zone_id` (e.g. mapping `4B` to `["4B-E1", "4B-E2", "4B-E3"]`).
  - Added scenario registration routing for `S6` pointing to the global runner loop.

### 3. Local Control Center Dashboard UI
- **[MODIFY] [src/control_center/templates/index.html](file:///d:/projects/IGNIS/src/control_center/templates/index.html)**:
  - Added an HTML control button mapping to start Scenario S6.
  - Updated the javascript node card visualizer (`updateEdgeCard`) to automatically create visual cards on the fly when reporting nodes with custom zone prefixes (such as `4B-E1`) register, clean-purging default placeholder mock cards.
  - Refactored the events ticker logic (`appendEventLog`) to extract the exact node ID that triggered an alert dynamically rather than showing hardcoded `E12` strings.

### 4. Verification & Validation Tests
- **[MODIFY] [tests/test_lateral_coordination.py](file:///d:/projects/IGNIS/tests/test_lateral_coordination.py)**:
  - Added `test_lateral_spread_scenario_generation()` verifying the correctness of all generated steps, sensor limits, and wind directions.

---

## Verification & Validation Results

### Unit Test Execution
All unit tests in the project run successfully:
```bash
python -m unittest discover tests
```
Output:
```text
Ran 26 tests in 0.028s

OK
```
