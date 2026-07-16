# Phase F2 Testing: Metrics Collector Hardening

This document outlines the testing strategy, test cases, and execution procedures for Phase F2 (Metrics Collector Hardening).

---

## Test Strategy

The hardened metrics collector is validated using unit tests that mock the input raw results structures. Testing focuses on verifying statistical computation correctness, Student-t CI boundary calculations (with and without the scipy package), assertion checks under passing/failing constraints, and verification of schema integrity.

---

## Test Cases Defined (`tests/test_metrics_collector.py` and `tests/test_chaos_resilience.py`)

### 1. Decision Latency Calculation
- **`test_calculate_decision_latency_valid`**: Feeds mock S3 trial results and verifies that `sample_count`, `min`, `max`, `mean`, `median`, and `confidence95` are correctly aggregated.
- **`test_calculate_decision_latency_empty`**: Asserts that running empty event structures returns `INVALID` status with a descriptive reason rather than hardcoded fake statistics.

### 2. Lateral Propagation Calculation
- **`test_calculate_lateral_propagation_valid`**: Runs a mock trial execution of S6 and verifies propagation delays between zone state updates.
- **`test_calculate_lateral_propagation_empty`**: Asserts that running empty event structures returns `INVALID` status.

### 3. False Positive Rate
- **`test_calculate_false_positive_rate_valid`**: Feeds mock sensor faults (S4) and checks the calculated false positive rate and clamp ratios.

### 4. Continuity & Message Separation
- **`test_calculate_offline_continuity_valid`**: Tests local execution buffer volume and flush rate calculation metrics under cloud disconnect warnings.
- **`test_calculate_concurrent_zone_integrity_valid`**: Asserts the detection of message cross-talk under parallel multi-zone simulations.

### 5. Multi-Scenario Aggregation & Assertions
- **`test_compute_metrics_all_scenarios`**: Validates the overall schema compilation, checking the nested dict structures, scenario status evaluations, overall summary counts, and reproducibility metadata.
- **`test_metrics_calculation_logic`** (`tests/test_chaos_resilience.py`): Re-verifies that legacy keys are maintained to preserve backward compatibility.

---

## Verification Execution

### Run F2 Unit Tests
To run the metrics calculation tests:
```powershell
python -m unittest tests/test_metrics_collector.py
```

### Run Full Test Suite
To confirm that F2 edits did not introduce regressions across other modules:
```powershell
python -m unittest discover tests
```
