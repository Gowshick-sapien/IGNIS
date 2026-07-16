# Phase F Consolidated Walkthrough: Scenario Library & Reporting

This document provides a comprehensive consolidated walkthrough of Phase F (Scenario Library & Reporting) implementation for the IGNIS project. It details the progression from validating YAML configuration schemas to executing statistical trials and compiling publication-ready markdown reports.

---

## 1. Phase F1: YAML Scenario Schema Hardening

Phase F1 establishes structured schemas, verification requirements, and simulation-specific eco-profile metadata inside the test scenario library to ensure all configurations are valid, clean, and tamper-evident before execution.

### Scenario Schema Enrichment (`scenarios/*.yaml`)
All seven test scenarios (`s1_normal.yaml` through `s7_multi_zone.yaml`) have been enriched with verification requirements and simulation context metadata:
- **`validation`**: Standard rules for automated trial verification.
  - `require_events` (bool): Asserts that events were collected.
  - `min_event_count` (int): Minimum required event entries.
  - `timeout_sec` (int): Duration threshold before timing out execution.
  - `assertions` (list): Assertion rules using metrics, operators (`<=`, `==`, `<`, `>=`, `>`, `!=`), and thresholds.
- **`metadata`**: Simulation context describing the eco-profile (e.g., `forest_type`, `zone_profile`).
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
- **Statistical Aggregation**: Computes sample size, min, max, mean, median, sample standard deviation, and a 95% confidence interval (CI) for all numerical metrics.
- **Student-t Confidence Intervals**: Uses `scipy.stats.t.interval()` if available. Otherwise, falls back to a custom precomputed critical values table (indexes $df = 1$ to $29$, mapped to $\alpha = 0.05$ two-tailed test bounds) to avoid forced external dependencies.
- **Dynamic Assertions**: Evaluates metrics dynamically against operators (`<=`, `==`, `<`, `>=`, `>`, `!=`) defined under the YAML configuration's `validation.assertions` block.
- **Nested Schema Mapping**: Restructured final output schemas to group outputs per scenario: `{status, reason, trials, metrics: {metric_name: {statistics_or_value, status, reason, threshold, operator}}}`.

### Reproducibility Metadata
Every metrics run outputs an `experiment_metadata` dictionary containing details needed to replicate the trial parameters:
- **RNG Seeding and Trials**: Trial count and execution seed values.
- **System and platform**: OS version, machine CPU architecture, timezone, hostnames, and Python versions.
- **Git Provenance**: Automatically retrieves the active git commit hash.
- **Scenario integrity**: Collects SHA-256 scenario checksums and version tags.

---

## 3. Phase F3: Experiment Orchestrator

Phase F3 implements a unified orchestrator CLI script `src/run_experiment.py` that links configuration schema validation, clean executions, raw trial runs, statistical calculation, chart and report updates, and reproducibility manifest logging into a single automated pipeline.

### Pipeline Implementation (`src/run_experiment.py`)
The orchestrator script establishes a robust 9-stage execution sequence:
1. **YAML Validation (Stage 1)**: Invokes `YamlValidator` to check all configuration structures and checksums. If errors are found, the pipeline aborts.
2. **Clean Outputs (Stage 2)**: Purges previous output results files and charts if the `--clean` flag is set.
3. **Run Scenarios (Stage 3)**: Executes target scenarios S1–S7 sequentially for the requested trials. Integrates a deterministic global random seed.
4. **Verify Completeness (Stage 4)**: Verifies that each executed scenario produced event records.
5. **Compute Metrics (Stage 5)**: Invokes `compute_metrics` to compute aggregates and evaluate assertions.
6. **Generate Charts (Stage 6)**: Updates Matplotlib visualizations under the target reports directory.
7. **Generate Report (Stage 7)**: Compiles the final results markdown writeup.
8. **Generate Manifest (Stage 8)**: Exposes run parameters, system environment variables, git hashes, and file paths.
9. **Summary Table (Stage 9)**: Outputs a clean tabular overview of scenario pass/fail results to stdout.

---

## 4. Phase F4: Consolidated Report Generator

Phase F4 implements the reporting and visualization layer of the IGNIS simulation results pipeline. It expands the metrics reporting system by generating 10 publication-ready Matplotlib charts using raw trial datasets, and compiling a comprehensive, dissertation-ready results writeup containing 9 research sections.

### Publication-Style Visualizations
The report generator automatically creates 10 printer-friendly Matplotlib visualizations. All charts are configured with white backgrounds, clean grids, and grayscale-compatible palettes:
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

### 9-Section Report Compiler (`src/report_generator.py`)
Compiles the results into `project_results_report.md` following standard dissertation structure:
1. **Executive Summary**: Overall compliance verdict and statistics.
2. **Experimental Setup**: Specific trial parameters, database versions, broker configs, and system environment details.
3. **Scenario Execution**: Summary result tables and execution gantt timeline.
4. **Experimental Results**: Dedicated sections for scenarios S1-S7 containing raw tables and relevant charts.
5. **Cross-Scenario Analysis**: Duration and scalability comparison.
6. **Architecture Validation Summary**: Mapping empirical evidence to Section 12 core architecture claims.
7. **Discussion**: Analysis of latencies against performance targets.
8. **Limitations**: Gaps relating to synthetic datasets and simulated RF environments.
9. **Conclusion**: Compliance verdict and recommendations.
