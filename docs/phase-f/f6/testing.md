# Phase F6 Testing: Tests

This document outlines the testing strategy, verification steps, and execution procedures for Phase F6 (Tests).

---

## Test Strategy

The testing strategy focuses on executing the test suite itself to verify that report compiler schemas, image counts, exception clamping, Student-t CI lookup fallbacks, and directory defaults are mathematically correct and functionally resilient.

---

## Verification Cases

### 1. Dissertation Structuring
- Execute `test_report_generator_dissertation_structure` and confirm that all 9 dissertation section headers are successfully written and all platform variables match environment metadata.

### 2. Plot Visualizations
- Execute `test_report_charts_generation` and verify that exactly 10 customized charts are written to disk.

### 3. Fail-Safe Resiliency
- Execute `test_report_chart_failure_resilience` and check that matploblib exceptions are caught, logged, and bypassed, outputting a partial chart array rather than crashing.

### 4. CI Calculations Fallback
- Execute `test_ci_method_fallback_statistics` and verify that patching out scipy stats forces the metrics collector to use the internal t-table without mathematical drift.

### 5. Ingestion Fail-safe
- Execute `test_load_raw_results_fallback` and confirm that invalid path parameters fall back to mock trial datasets.

---

## Verification Execution

### Run F6 Unit Tests
To run the report pipeline unit tests:
```powershell
python -m unittest tests/test_report_pipeline.py
```

### Run Full Test Suite
To confirm that all changes do not introduce regressions across other modules:
```powershell
python -m unittest discover tests
```
All 74 unit tests in the repository must pass successfully with exit code 0.
