# Phase E6 Testing: Metrics Collector & Report Generator

This document outlines the testing strategy, test cases, and execution procedures for Phase E6 (Metrics Collector & Report Generator).

## Test Strategy

To verify the collector math and report compile routines safely without requiring graphical displays or disk IO bottlenecks inside clean-room test environments:
1. **Mock Data Feeding**: We feed structured trial list dictionaries directly to the metrics calculation methods and assert correct values.
2. **Matplotlib Mocking**: We mock the `matplotlib.pyplot.savefig` interface to verify the charts are generated without actually writing image files.
3. **IO Mocking**: We patch `builtins.open` to verify report compile writes.
4. **Initialization Isolation**: We patch `builtins.open` only *after* imports are finished inside the test function, preventing side-effects on Matplotlib's internal loaders.

---

## Test Cases Defined (`tests/test_chaos_resilience.py`)

### 1. Metrics Calculation Logic (`test_metrics_calculation_logic`)
- **Objective**: Verify that averages, false-positive counts, and propagation deltas are computed accurately.
- **Procedure**:
  1. Feed mock results containing timestamps and states.
  2. Verify `calculate_decision_latency` outputs correct difference (e.g. 1.2s).
  3. Verify `calculate_lateral_propagation` captures bearing-propagation delta.
  4. Verify `calculate_false_positive_rate` maps to correctly computed ratios.
  5. Verify `calculate_offline_continuity` counts enqueued vs flushed records.

### 2. Report Generator (`test_report_generator`)
- **Objective**: Verify chart plotting triggers and markdown report compilation writes.
- **Procedure**:
  1. Patch `matplotlib.pyplot.savefig` and `builtins.open`.
  2. Invoke `generate_charts()` and assert that exactly 5 calls are dispatched to `savefig()`.
  3. Invoke `generate_report()` and assert that the report file is opened and written.

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
All 51 tests in the repository will execute and pass cleanly.
