# Phase F3 Testing: Experiment Orchestrator

This document outlines the testing strategy, test cases, and execution procedures for Phase F3 (Experiment Orchestrator).

---

## Test Strategy

The experiment orchestrator pipeline is validated using unit tests that mock external scenario runner loops and chart generation tools. Testing focuses on verifying output directory cleaning, YAML validation failure handling, deterministic replay behaviors, and correct metadata manifest assembly.

---

## Test Cases Defined (`tests/test_run_experiment.py`)

### 1. Cleaning Stale Outputs
- **`test_pipeline_clean_removes_old_files`**: Asserts that `clean_outputs()` successfully purges legacy results configuration files (`stale_result.json`) and markdown reports (`project_results_report.md`) from target output folders.

### 2. Full Pipeline Ingestion
- **`test_run_experiment_full_pipeline`**:
  - Mocks the `sys.argv` command arguments.
  - Mocks `ScenarioRunner.run_scenario()` to return a simulated `ScenarioResult` object.
  - Runs the orchestrator pipeline.
  - Verifies that `raw_results.json`, `metrics.json`, and `experiment_manifest.json` are created inside the output directory.
  - Asserts that the random seed is correctly set and output structure fields (such as platform variables and metrics status PASS) are present.

---

## Verification Execution

### Run F3 Unit Tests
To run the orchestrator unit tests:
```powershell
python -m unittest tests/test_run_experiment.py
```

### Run Full Test Suite
To confirm that F3 edits did not introduce regressions across other modules:
```powershell
python -m unittest discover tests
```
