# Phase F Consolidated Testing: Scenario Library & Reporting

This document details the consolidated testing approach, automated unit test cases, and a comprehensive step-by-step manual testing guide for Phase F (Scenario Library & Reporting).

---

## 1. Testing Strategy

To verify the components of Phase F safely, deterministically, and in isolation without requiring active container networks or live chaos injection, the test suite leverages the following strategy:
1. **Mocked Scenario Runner Loops**: Bypasses active MQTT publish/subscribe pipelines using precalculated dataclass outcomes or direct object mocks.
2. **System Environment Mocking**: Employs `unittest.mock.patch` on `sys.argv`, `sys.modules`, and subprocess operations to check platform portability, clean commands, CLI arguments, and git hashes.
3. **Resilient Failure Injection**: Mocks chart failures to ensure report generation compiles correctly under best-effort fallback constraints.
4. **Dynamic Schema Validation**: Validates YAML schemas against specific structural violations and assertion failures.

---

## 2. Unit Test Cases

### Phase F1: YAML Scenario Schema Hardening (`tests/test_yaml_validator.py`)
- `test_valid_scenarios_pass`: Validates all seven production YAML files in `scenarios/`.
- `test_missing_required_keys`: Omit critical keys (e.g. `validation`) and asserts validation failure.
- `test_invalid_assertion_operator`: Rejects invalid mathematical operators (e.g. `=>`).
- `test_invalid_target_mode`: Catches invalid zone profiles or incorrect target mode declarations.
- `test_checksum_generation`: Confirms SHA-256 hashes remain stable and tamper-evident.

### Phase F2: Metrics Collector Hardening (`tests/test_metrics_collector.py` & `tests/test_chaos_resilience.py`)
- `test_calculate_decision_latency_valid`: Feeds mock S3 events and checks aggregated stats.
- `test_calculate_decision_latency_empty`: Verifies that empty event streams produce `INVALID` status.
- `test_calculate_lateral_propagation_valid`: Checks warning coordination elapsed time.
- `test_calculate_false_positive_rate_valid`: Checks clamping and false positive rates.
- `test_calculate_offline_continuity_valid`: Validates cached message sizes and recovery flushes.
- `test_calculate_concurrent_zone_integrity_valid`: Verifies message separation during crosstalk.
- `test_compute_metrics_all_scenarios`: Tests schema compilation and metadata output.
- `test_calculate_stats_zero_variance`: Verifies constant datasets produce deterministic `[0.0, 0.0]` bounds without `NaN` or warnings.
- `test_metrics_calculation_logic` (`tests/test_chaos_resilience.py`): Checks that legacy properties remain for backwards compatibility.

### Phase F3: Experiment Orchestrator (`tests/test_run_experiment.py`)
- `test_pipeline_clean_removes_old_files`: Asserts that `clean_outputs()` successfully purges legacy results folders.
- `test_run_experiment_full_pipeline`: Mocks argument parsing, scenario execution, and validates generation of manifest files.

### Phase F4: Consolidated Report Generator (`tests/test_report_pipeline.py` & `tests/test_chaos_resilience.py`)
- `test_report_generator_dissertation_structure`: Verifies 9 dissertation sections exist and contain correct platform info.
- `test_report_charts_generation`: Checks that exactly 10 PNG charts are successfully written to disk.
- `test_report_generator` (`tests/test_chaos_resilience.py`): Asserts that exactly 10 mock savefig dispatches are completed.
- `test_report_chart_failure_resilience`: Mocks exceptions on individual Matplotlib saves to verify best-effort compilation.
- `test_ci_method_fallback_statistics`: Simulates a system without scipy to verify Student-t lookup fallback boundaries.
- `test_load_raw_results_fallback`: Confirms that invalid directories fall back to structured mock datasets.

### Phase F5: Consistency & Replay Regression (`tests/test_report_consistency.py`)
- `test_all_pass_execution`: Mock all-passing scenario outcomes and checks dynamic executive summaries, key findings, and validation table verdicts.
- `test_all_fail_execution`: Mock all-failing scenario outcomes and verifies dynamic discussions, limitations, and failure reasons.
- `test_mixed_execution`: Mocks mixed statuses (PASS, FAIL, INVALID) and verifies that findings and tables represent correct statuses.
- `test_all_invalid_execution`: Checks that reports dynamically fall back to "Metric unavailable" and "Not Validated".
- `test_deterministic_replay`: Verifies that identical seeds produce identical metrics and report contents.

---

## 3. Automated Test Execution

### Run Only Phase F Tests
To execute orchestrator, validator, metrics, and reporting test files:
```powershell
python -m unittest tests/test_yaml_validator.py tests/test_metrics_collector.py tests/test_run_experiment.py tests/test_report_pipeline.py tests/test_report_consistency.py
```

### Run Full Test Suite
To confirm that no regressions are introduced in other modules:
```powershell
python -m unittest discover tests
```
All 80 tests in the repository must pass cleanly.

---

## 4. Detailed Manual Verification Guide

This guide describes how to run and verify the entire Phase F implementation manually, from container execution to live metrics reporting, deterministic seed replays, and file structure audits.

### Step 1: Startup the Simulation Environment
1. Ensure **Docker Desktop** is running.
2. Spin up the local broker networks and dashboard containers in detached mode from the project root:
   ```powershell
   docker compose up --build -d
   ```
3. Verify that all container interfaces are healthy:
   ```powershell
   docker compose ps
   ```
   You should see `mqtt-broker-local`, `fog-node`, `edge-sim`, `cloud-broker`, `influxdb`, and `cloud-dashboard` containers running.
4. Launch the local Chaos Controller API listener on the host machine:
   ```powershell
   python -m src.chaos_controller.app
   ```
   Confirm that the console log reads: `Started server process [...] Uvicorn running on http://127.0.0.1:9001`.

---

### Step 2: Execute the Pipeline Orchestrator (Single-Command Run)
1. Run the experiment orchestrator pipeline to validate configuration schemas, run scenario trials, and generate reports:
   ```powershell
   python -m src.run_experiment --trials 10 --clean
   ```
2. Observe the terminal output stages. Ensure they progress chronologically:
   - **Stage 1 (Validation)**: Validator parses and checksums all YAML configs.
   - **Stage 2 (Cleaning)**: Deletes previous contents of the `results/` folder and `docs/phase-f/charts/` directory.
   - **Stage 3 (Scenario Runs)**: Runs S1 through S7 sequentially. In the console, check for logs indicating that trials are executing and triggering chaos events.
   - **Stage 4 (Completeness)**: Inspects outcomes to ensure trials generated events.
   - **Stage 5 (Compute Metrics)**: Aggregates metrics and evaluates schema assertions.
   - **Stage 6 (Generate Charts)**: Renders Matplotlib PNGs under `docs/phase-f/charts/`.
   - **Stage 7 (Generate Report)**: Writes `docs/phase-f/project_results_report.md`.
   - **Stage 8 (Manifest)**: Writes metadata config mapping to `results/experiment_manifest.json`.
   - **Stage 9 (Summary Table)**: Prints a results overview table.

---

### Step 3: Verify Deterministic Seeding and Replays
To confirm the pipeline's deterministic reproducibility behavior:
1. Run the orchestrator with a specific seed and separate output/report targets:
   ```powershell
   python -m src.run_experiment --trials 5 --clean --seed 4321 --output-dir results/run_a --report-dir docs/phase-f/run_a
   ```
2. Run a second execution using the identical parameters and seed:
   ```powershell
   python -m src.run_experiment --trials 5 --clean --seed 4321 --output-dir results/run_b --report-dir docs/phase-f/run_b
   ```
3. Use a file comparison utility to assert that the computed averages, standard deviations, and intervals are identical:
   ```powershell
   Compare-Object (Get-Content results/run_a/metrics.json) (Get-Content results/run_b/metrics.json)
   ```
   No output differences should be returned, validating deterministic replay.

---

### Step 4: Manual Document and Chart Audit
Inspect the generated directory structures to confirm correctness:
1. Open the [metrics.json](file:///d:/projects/IGNIS/results/metrics.json) file:
   - Verify that statistical aggregates (`mean`, `min`, `max`, `median`, `std_dev`, `confidence95`) are present under numeric fields.
   - Confirm the `"platform"` block is structured and records machine architectures, Python versions, and timezones.
2. Open the [experiment_manifest.json](file:///d:/projects/IGNIS/results/experiment_manifest.json) file:
   - Verify `git_commit` displays the current active commit hash.
   - Confirm scenario files checksum mappings are populated.
3. Open the [experiment.log](file:///d:/projects/IGNIS/results/logs/experiment.log) file:
   - Confirm logs follow standard format and contain entry/exit timings for all 9 stages.
4. Navigate to `docs/phase-f/charts/` and inspect visual styling:
   - Verify the charts use a clean white background.
   - Open `lateral_propagation_ci.png` and check that error bounds are plotted.
   - Open `message_integrity_heatmap.png` and verify cell annotations.
   - Open `execution_timeline.png` and confirm Gantt horizontal blocks render cleanly.
5. Open [project_results_report.md](file:///d:/projects/IGNIS/docs/phase-f/project_results_report.md) in a markdown reader:
   - Confirm all 9 dissertation sections compile.
   - Verify that the Section 6 Architecture Validation Table contains checkmark symbols (`✅`) indicating validated status.
   - Ensure all image tags link correctly to `charts/`.

---

### Step 5: Verify Development Mode (Loading Cache Results)
To confirm developers can iterate on visualizations/reports without re-running container simulations:
1. Run the script with `--load-existing` argument:
   ```powershell
   python -m src.run_experiment --load-existing --trials 10
   ```
2. Verify that:
   - The orchestrator skips Stage 3 (Scenario execution) entirely.
   - Charts and reports are rebuilt instantly.
   - The CLI exits with code 0.
