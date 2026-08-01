# Phase F Consolidated Walkthrough: Scenario Library & Reporting

This document provides a comprehensive consolidated walkthrough of Phase F (Scenario Library & Reporting) implementation for the IGNIS project. It details the progression from validating YAML configuration schemas to executing statistical trials and compiling publication-ready markdown reports.

---

## 1. Phase F1: YAML Scenario Schema Hardening

Phase F1 establishes structured schemas, verification requirements, and simulation-specific eco-profile metadata inside the test scenario library to ensure all configurations are valid, clean, and tamper-evident before execution.

### Scenario Schema Enrichment (`scenarios/`)
All seven test scenarios (`s1_normal.yaml` through `s7_multi_zone.yaml`) have been enriched with verification requirements and simulation context metadata:
- **`validation`**: Standard rules for automated trial verification.
  - `require_events` (bool): Asserts that events were collected.
  - `min_event_count` (int): Minimum required event entries.
  - `timeout_sec` (int): Duration threshold before timing out execution.
  - `assertions` (list): Assertion rules using metrics, operators (`<=`, `==`, `<`, `>=`, `>`, `!=`), and thresholds.
- **`metadata`**: Simulation context describing the eco-profile (e.g., `forest_type`: `"dry_deciduous"`, `zone_profile`: `"simlipal_core"`).
- **`metrics_targets`**: Updated performance thresholds to align with the metric verification system.

### Schema Validation Utility (`src/scenarios/yaml_validator.py`)
A schema validation class `YamlValidator` was introduced to load, parse, validate, and compute checksums for all scenarios:
- **`validate(yaml_path: str) -> dict`**:
  - Verifies presence of all required root keys (`scenario_id`, `description`, `version`, `target`, `steps`, `expected_outcome`, `metrics_targets`, `validation`).
  - Checks target configuration: ensures mode is one of `global`, `localized`, or `multi_zone`, and `zone_ids` is list-structured.
  - Evaluates step components: validates presence of `index`, `duration_sec`, `sensor_data`, and `seasonal_baseline`.
  - Audits `validation` blocks: verifies type constraints (`require_events`, `min_event_count`, `timeout_sec`) and tests every validation assertion for valid metric names, supported operators, and threshold values.
- **`validate_all(scenarios_dir: str) -> list[dict]`**: Automatically runs `validate` across all scenario configuration files.
- **`checksum(yaml_path: str) -> str`**: Generates binary-safe SHA-256 hex digests of the target configuration file to ensure tamper-evident execution.
- **`checksum_all(scenarios_dir: str) -> dict[str, str]`**: Generates checksum mappings for all valid scenarios.

---

## 2. Phase F2: Metrics Collector Hardening

Phase F2 hardens the simulation metrics collection and reporting by removing mock fallback values, implementing robust statistical methods (including Student-t confidence intervals), and gathering platform reproducibility metadata.

### Calculation Engine Modifications (`src/metrics_collector.py`)
- **Fallback Elimination**: Mock arrays for latency and propagation times have been deleted. If a scenario lacks target events, it is flagged as `INVALID` with a descriptive reason.
- **Statistical Aggregation & Canonical Schema**: Computes sample size, minimum, maximum, mean, median, sample standard deviation, and a 95% confidence interval (CI) for all numerical metrics. Legacy aliases (`min`, `max`) are retained to preserve backwards compatibility with the NOC Cloud Dashboard.
- **Student-t Confidence Intervals & Zero-Variance NaN Safeguard**: Uses `scipy.stats.t.interval()` if available. Automatically detects constant or zero-variance datasets (`val_std == 0.0` or `val_min == val_max`) and returns deterministic bounds `confidence95 = [mean, mean]` (`[0.0, 0.0]`) without calling SciPy, completely suppressing SciPy `RuntimeWarning` multiply warnings and eliminating `NaN` values in `metrics.json` and generated reports.
- **Dynamic Assertions & Clean Unit Evaluation**: Evaluates metrics dynamically against operators (`<=`, `==`, `<`, `>=`, `>`, `!=`) defined under the YAML configuration's `validation.assertions` block. Cleans unit prefixes (e.g. removes datatype units like `bool`, `count`, `ratio`, `state`).
- **Assertion Failure Formatting**: Formats failed assertion outcomes cleanly (e.g., `Assertion Failed: Expected: True, Observed: False` or `Assertion Failed: Expected: 0, Observed: 5`) instead of printing raw mathematical comparison strings.
- **Nested Schema Mapping**: Restructured final output schemas to group outputs per scenario: `{status, reason, trials, metrics: {metric_name: {statistics_or_value, status, reason, threshold, operator}}}`.

### Reproducibility Metadata
Every metrics run outputs an `experiment_metadata` dictionary containing details needed to replicate the trial parameters:
- **RNG Seeding and Trials**: Trial count and execution seed values.
- **System and platform**: OS version, machine CPU architecture, timezone, hostnames, Python runtime versions, and dynamically resolved **Docker & Docker Compose versions** (`docker --version` / `docker compose version`).
- **Git Provenance**: Automatically retrieves the active git commit hash.
- **Scenario integrity**: Collects SHA-256 scenario checksums and version tags.

---

## 3. Phase F3: Experiment Orchestrator

Phase F3 implements a unified orchestrator CLI script [run_experiment.py](file:///d:/projects/IGNIS/src/run_experiment.py) that links configuration schema validation, clean executions, raw trial runs, statistical calculation, chart and report updates, and reproducibility manifest logging into a single automated pipeline.

### Pipeline Implementation (`src/run_experiment.py`)
The orchestrator script establishes a robust 9-stage execution sequence:
1. **YAML Validation (Stage 1)**: Invokes `YamlValidator` to check all configuration structures and checksums. If errors are found, the pipeline aborts.
2. **Clean Outputs (Stage 2)**: Purges previous output results files and charts if the `--clean` flag is set.
3. **Run Scenarios (Stage 3)**: Executes target scenarios S1–S7 sequentially for the requested trials. Integrates a deterministic global random seed and propagates this seed down to individual edge simulators using MQTT control command payloads.
4. **Verify Completeness (Stage 4)**: Verifies that each executed scenario produced event records.
5. **Compute Metrics (Stage 5)**: Invokes `compute_metrics` to compute aggregates and evaluate assertions.
6. **Generate Charts (Stage 6)**: Updates Matplotlib visualizations under the target reports directory.
7. **Generate Report (Stage 7)**: Compiles the final results markdown writeup.
8. **Generate Manifest (Stage 8)**: Exposes run parameters, system environment variables, git hashes, and file paths.
9. **Summary Table (Stage 9)**: Outputs a clean tabular overview of scenario pass/fail results to stdout.

### Deterministic Event Sorting & Replay
- **Stable Multi-Level Sort**: Captures and deterministic-sorts all events compiled in `raw_results.json` using Trial Index, Scenario ID, Timestamp, Zone ID, Message Type, Source Node, MQTT Topic, and SHA-256 payload hash as the absolute tie-breaker.
- **Event-Driven Sleep & Reset**: Telemetry generators use `threading.Event.wait` instead of unaligned sleep timers, allowing control overrides to immediately wake nodes and publish, ensuring identical event arrival order under identical seed parameters.

---

## 4. Phase F4: Consolidated Report Generator

Phase F4 implements the reporting and visualization layer of the IGNIS simulation results pipeline. It expands the metrics reporting system by generating 10 publication-ready Matplotlib charts using raw trial datasets, and compiling a comprehensive, dissertation-ready results writeup containing 9 research sections.

### Publication-Style Visualizations
The report generator [report_generator.py](file:///d:/projects/IGNIS/src/report_generator.py) automatically creates 10 printer-friendly Matplotlib visualizations. All charts are configured with white backgrounds, clean grids, and grayscale-compatible palettes:
- **`decision_latency_boxplot.png`**: Box plot depicting the variance and median value of S3 decision latencies.
- **`decision_latency_histogram.png`**: Density distribution histogram of S3 decision latencies.
- **`lateral_propagation_comparison.png`**: Bar chart comparison of adjacent zone warn coordination durations across trials (S6).
- **`lateral_propagation_ci.png`**: Statistical interval chart displaying the S6 mean propagation time alongside its 95% Student-t confidence intervals.
- **`false_positive_trend.png`**: Line plot showcasing the cumulative false-positive rate trend during sensor failures (S4).
- **`offline_buffering_timeline.png`**: Grouped bar chart tracking the message caching and flushing timeline during local standalone operations (S5).
- **`message_integrity_heatmap.png`**: Annotated crosstalk matrix showing message mapping by zone during simultaneous outbreaks (S7).
- **`scenario_comparison_summary.png`**: Comparative bar chart of mean execution durations across all scenarios.
- **`state_transition_timeline.png`**: Step-wise state transition timeline showing GREEN -> YELLOW -> ORANGE -> RED progression (S3).
- **`execution_timeline.png`**: Gantt-style horizontal timeline representing pipeline scenario ordering and durations.

### Visual Polish & Placeholder Support
- **Guideline-Compliant Titles**: Updated titles in S6 propagation plot and S7 crosstalk heatmap (e.g. `Scenario S6\nMean Lateral Propagation Time\n(95% Confidence Interval)`) for improved visual appeal.
- **Empty Timeline Fallbacks**: Renders placeholder text (`No events captured during experiment`) instead of empty charts if the Scenario S5 buffering dataset contains no records.

### Dynamic 9-Section Report Compiler
Compiles the results dynamically into `project_results_report.md` following standard dissertation structure based on the actual execution results:
1. **Executive Summary**: Dynamically derives compliance verdict, breakdown counts, and key findings.
2. **Experimental Setup**: Specific trial parameters, database versions, broker configs, and system environment details.
3. **Scenario Execution**: Summary result tables and execution gantt timeline.
4. **Experimental Results**: Dedicated sections for scenarios S1-S7 containing raw tables (marked with "Metric unavailable" for empty/invalid runs) and relevant charts.
5. **Cross-Scenario Analysis**: Dynamic narrative summarizing passes, fails, and invalid runs.
6. **Architecture Validation Summary**: Generates a validation table mapping actual outcomes (`[PASS] Validated`, `[FAIL] Validation Failed`, or ` Not Validated`) to claims based on empirical evidence.
7. **Discussion**: Analysis of decision latency, offline continuity, and concurrent integrity dynamically.
8. **Limitations**: Gaps relating to synthetic datasets and simulated RF environments.
9. **Conclusion**: Compliance verdict and recommendations derived entirely from actual verdicts.

---

## 5. Phase F5: Documentation & README Update

Phase F5 finalizes the Scenario Library & Reporting phase by updating the project's repository README, modifying the design architecture document, and compiling technical walkthrough and testing procedures.

- **`README.md`**: Updated Project Phases status fields, inserted technical overviews of completed Phases C-F, updated directory layouts, and added orchestrator command line running parameters.
- **`docs/architecture.md`**: Updated Section 13 (Development Phases) flowchart with labels and detailed descriptions of Phase F's verification layer.

---

## 6. Phase F6: Tests

Phase F6 implements a unified, automated test suite [test_report_pipeline.py](file:///d:/projects/IGNIS/tests/test_report_pipeline.py) verifying report structure, image outputs, exception resilience, and Student-t fallback calculations in isolation.

Additionally, a comprehensive regression test suite [test_report_consistency.py](file:///d:/projects/IGNIS/tests/test_report_consistency.py) was added to verify:
- Dynamic compilation of all-pass metrics.
- Dynamic compilation of all-fail metrics.
- Dynamic compilation of mixed pass/fail/invalid metrics.
- Fallbacks to metric unavailable formats.
- Deterministic replay of statistical runs.

All 80 unit tests in the repository pass cleanly.
