# Phase F Consolidated Testing: Scenario Library & Reporting

This document details the consolidated testing approach, test cases, and execution guidelines for Phase F (Scenario Library & Reporting).

## Testing Strategy

To verify the components of Phase F safely, deterministically, and in isolation without requiring active container networks or live chaos injection, the test suite leverages the following strategy:
1. **Mocked Scenario Runner Loops**: Bypasses active MQTT publish/subscribe pipelines using precalculated dataclass outcomes or direct object mocks.
2. **System Environment Mocking**: Employs `unittest.mock.patch` on `sys.argv`, `sys.modules`, and subprocess operations to check platform portability, clean commands, CLI arguments, and git hashes.
3. **Resilient Failure Injection**: Mocks chart failures to ensure report generation compiles correctly under best-effort fallback constraints.
4. **Dynamic Schema Validation**: Validates YAML schemas against specific structural violations and assertion failures.

---

## Unit Test Cases

### 1. Phase F1: YAML Scenario Schema Hardening (`tests/test_yaml_validator.py`)
- `test_valid_scenarios_pass`: Validates all seven production YAML files in `scenarios/`.
- `test_missing_required_keys`: Omit critical keys (e.g. `validation`) and asserts validation failure.
- `test_invalid_assertion_operator`: Rejects invalid mathematical operators (e.g. `=>`).
- `test_invalid_target_mode`: Catches invalid zone profiles or incorrect target mode declarations.
- `test_checksum_generation`: Confirms SHA-256 hashes remain stable and tamper-evident.

### 2. Phase F2: Metrics Collector Hardening (`tests/test_metrics_collector.py` & `tests/test_chaos_resilience.py`)
- `test_calculate_decision_latency_valid`: Feeds mock S3 events and checks aggregated stats.
- `test_calculate_decision_latency_empty`: Verifies that empty event streams produce `INVALID` status.
- `test_calculate_lateral_propagation_valid`: Checks warning coordination elapsed time.
- `test_calculate_false_positive_rate_valid`: Checks clamping and false positive rates.
- `test_calculate_offline_continuity_valid`: Validates cached message sizes and recovery flushes.
- `test_calculate_concurrent_zone_integrity_valid`: Verifies message separation during crosstalk.
- `test_compute_metrics_all_scenarios`: Tests schema compilation and metadata output.
- `test_metrics_calculation_logic` (`tests/test_chaos_resilience.py`): Checks that legacy properties remain for backwards compatibility.

### 3. Phase F3: Experiment Orchestrator (`tests/test_run_experiment.py`)
- `test_pipeline_clean_removes_old_files`: Asserts that `clean_outputs()` successfully purges legacy results folders.
- `test_run_experiment_full_pipeline`: Mocks argument parsing, scenario execution, and validates generation of manifest files.

### 4. Phase F4: Consolidated Report Generator (`tests/test_report_pipeline.py` & `tests/test_chaos_resilience.py`)
- `test_report_generator_dissertation_structure`: Verifies 9 dissertation sections exist and contain correct platform info.
- `test_report_charts_generation`: Checks that exactly 10 PNG charts are successfully written to disk.
- `test_report_generator` (`tests/test_chaos_resilience.py`): Asserts that exactly 10 mock savefig dispatches are completed.
- `test_report_chart_failure_resilience`: Mocks exceptions on individual Matplotlib saves to verify best-effort compilation.
- `test_ci_method_fallback_statistics`: Simulates a system without scipy to verify Student-t lookup fallback boundaries.
- `test_load_raw_results_fallback`: Confirms that invalid directories fall back to structured mock datasets.

---

## Verification Execution

### 1. Run Scenario Library & Reporting Test Suite
To run only the newly introduced Phase F orchestrator and reporting tests:
```powershell
python -m unittest tests/test_run_experiment.py tests/test_report_pipeline.py
```

### 2. Run Full Test Suite
To verify all changes do not introduce regressions across any module:
```powershell
python -m unittest discover tests
```
All 74 tests in the repository will be executed and should pass cleanly.
