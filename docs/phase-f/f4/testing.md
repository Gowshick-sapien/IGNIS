# Phase F4 Testing: Consolidated Report Generator

This document outlines the testing strategy, test cases, and execution procedures for Phase F4 (Consolidated Report Generator).

---

## Test Strategy

The report generator pipeline is validated using automated unit tests that inspect both output markdown structures and Matplotlib figure counts. Testing focuses on verifying 9-section report document integrity, 10-chart rendering completeness, resilient try/except fallback logic under matplotlib errors, and Student-t confidence interval manual fallback math when optional scipy packages are uninstalled.

---

## Test Cases Defined (`tests/test_report_pipeline.py` and `tests/test_chaos_resilience.py`)

### 1. Dissertation Structure Compilation
- **`test_report_generator_dissertation_structure`**: Generates a test report from dummy metrics and checks that all 9 required dissertation headers exist, alongside platform and platform reproducibility metadata.

### 2. Publication-Style Visualizations
- **`test_report_charts_generation`**: Generates Matplotlib charts from metrics and mock trial results and verifies that exactly 10 PNG charts are successfully written to the disk with matching filenames.
- **`test_report_generator`** (`tests/test_chaos_resilience.py`): Asserts that exactly 10 mock savefig dispatches are completed.

### 3. Fail-Safe Resiliency
- **`test_report_chart_failure_resilience`**: Injects mock matplotlib exceptions on specific charts and asserts that `generate_charts()` catches the error, continues writing the remaining charts, and returns the successful subset without crashing.

### 4. CI Calculations & Fallback
- **`test_ci_method_fallback_statistics`**: Simulates a system without scipy by patching `sys.modules` and asserts that statistical CI aggregates fall back to the internal lookup table without crashing.
- **`test_load_raw_results_fallback`**: Verifies that calling `load_raw_results()` on invalid paths falls back to structured mock datasets.

---

## Verification Execution

### Run F4 Unit Tests
To run the report pipeline unit tests:
```powershell
python -m unittest tests/test_report_pipeline.py
```

### Run Full Test Suite
To confirm that F4 edits did not introduce regressions across other modules:
```powershell
python -m unittest discover tests
```
